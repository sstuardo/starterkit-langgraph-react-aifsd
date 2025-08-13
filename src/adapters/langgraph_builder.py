"""
Compila el flujo ReAct en LangGraph con selector **parametrizable**.

Modos:
- selector_mode="static": enrutado determinístico con tus nodos:
  planner → reasoner → tool_selector? → tool_executor? → reasoner → critic → finalizer
- selector_mode="llm": usa ToolNode + tools_condition para que el **LLM decida** tools:
  planner → model → (tools?) → model → critic → finalizer

Notas:
- Los imports del modo LLM se hacen *dentro* de la función para no requerir deps opcionales
  cuando usas el modo estático.
- En el modo LLM se limita el ciclo a **una** ejecución de tools por invocación para evitar
  recursiones (se detecta un `ToolMessage` y se cierra el episodio).
"""

from __future__ import annotations

from langgraph.graph import StateGraph
from src.core.state import State
from src.react.planner import planner_node
from src.react.reasoner import reasoner_node
from src.react.tool_selector import tool_selector_node
from src.react.tool_executor import tool_executor_node, TOOL_REGISTRY
from src.react.critic import critic_node
from src.react.finalizer import finalizer_node
import os

FALLBACK_ENABLED = os.getenv("LLM_FALLBACK", "1") not in ("0", "false", "False")

def _compile_static():
    """Compila el grafo en modo **estático** (router determinístico)."""
    g = StateGraph(State)

    # Nodos
    g.add_node("planner", planner_node)
    g.add_node("reasoner", reasoner_node)
    g.add_node("tool_selector", tool_selector_node)
    g.add_node("tool_executor", tool_executor_node)
    g.add_node("critic", critic_node)
    g.add_node("finalizer", finalizer_node)

    # Entrada
    g.set_entry_point("planner")
    g.add_edge("planner", "reasoner")

    # Condiciones
    def decide_next(s: State) -> str:
        """Tras reasoner: si listo o sin presupuesto → critic; si no → selector."""
        if s.ready_to_answer or s.step >= s.max_steps:
            return "critic"
        return "tool_selector"

    def select_path(s: State) -> str:
        """Tras selector: si hay tool → ejecutor; si no → critic (evita bucles)."""
        return "tool_executor" if s.metadata.get("selected_tool") else "critic"

    g.add_conditional_edges("reasoner", decide_next, {
        "tool_selector": "tool_selector",
        "critic": "critic",
    })
    g.add_conditional_edges("tool_selector", select_path, {
        "tool_executor": "tool_executor",
        "critic": "critic",
    })

    # Tras ejecutar tools, volvemos a razonamiento
    g.add_edge("tool_executor", "reasoner")

    # Crítica → finalización directa (simple y estable)
    g.add_conditional_edges("critic", lambda s: "finalizer", {"finalizer": "finalizer"})

    # Fin
    g.set_finish_point("finalizer")
    return g.compile()

def _compile_llm():
    """Compila el grafo en modo **LLM** con:
    - Normalización segura del 1er turno (evita error 400).
    - Guard anti-loop (máx. 1 tool-call).
    - Fallback determinístico si el prompt pide explícitamente 'echo'.
    - Sincronización de evidencia (ToolMessage/artifacts) antes de cerrar.
    """
    from langgraph.prebuilt import ToolNode, tools_condition  # requiere langgraph>=0.3.1
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
    from src.adapters.lc_tool_bridge import to_structured_tools
    from src.core.observability import span
    import os

    lc_tools = to_structured_tools(TOOL_REGISTRY)
    model_id = os.getenv("LLM_MODEL", "gpt-4o-mini")
    llm = ChatOpenAI(model=model_id, temperature=0)
    llm_with_tools = llm.bind_tools(lc_tools)
    tool_node = ToolNode(lc_tools)

    SYSTEM_HINT = (
        "Eres un agente ReAct. Herramientas disponibles:\n"
        "- echo(text:str): devuelve exactamente el texto.\n"
        "Si el usuario pide repetir/eco o dice 'usa la herramienta echo', llama 'echo' UNA sola vez y luego responde."
    )

    def _prepare_first_turn(msgs, user_query):
        """Si aún no hubo AI, quita ToolMessages huérfanos y asegura System+Human."""
        has_ai = any(isinstance(m, AIMessage) for m in msgs)
        if has_ai:
            return msgs
        cleaned = [m for m in msgs if not isinstance(m, ToolMessage)]
        if not cleaned or not isinstance(cleaned[0], SystemMessage):
            cleaned = [SystemMessage(content=SYSTEM_HINT)] + cleaned
        if not any(isinstance(m, HumanMessage) for m in cleaned):
            cleaned = [cleaned[0], HumanMessage(content=user_query)] + cleaned[1:]
        return cleaned

    def _wants_echo(user_query: str) -> bool:
        q = user_query.lower()
        return ("usa la herramienta echo" in q) or ("usar la herramienta echo" in q) or (" echo " in f" {q} ")

    def model_node(state: State) -> State:
        with span("model", step=state.step):
            s = state.model_copy(deep=True)
            s.step += 1  # presupuesto/seguridad
            s.messages = _prepare_first_turn(s.messages, s.user_query)
            ai = llm_with_tools.invoke(s.messages)  # el modelo puede emitir tool_calls
            s.messages = s.messages + [ai]
            return s

    def model_router(state: State) -> str:
        """Cierre por presupuesto/ready; si ya hubo ToolMessage, cerramos;
        si el prompt pide 'echo', usamos fallback; si no, dejamos decidir al modelo.
        """
        if state.step >= state.max_steps or state.ready_to_answer:
            return "__end__"
        if any(isinstance(m, ToolMessage) for m in state.messages):
            return "__end__"
        if FALLBACK_ENABLED and _wants_echo(state.user_query):
            return "fallback"
        return tools_condition(state)  # "tools" o "__end__"

    def fallback_node(state: State) -> State:
        """Selector+ejecutor determinístico como respaldo (una pasada)."""
        with span("fallback", step=state.step):
            s = state.model_copy(deep=True)
            # Forzamos echo en esta ruta de respaldo
            s.metadata["selected_tool"] = "echo"
            s = tool_executor_node(s)
            # Marcamos listo para que el router cierre después de sync/critic
            s.ready_to_answer = True
            return s

    def sync_evidence_node(state: State) -> State:
        """Sincroniza ToolMessages/artifacts → working_memory + confianza."""
        with span("sync", step=state.step):
            s = state.model_copy(deep=True)
            # 1) Volcar ToolMessages (si existieran) a artifacts/observations
            tool_msgs = [m for m in s.messages if isinstance(m, ToolMessage)]
            for tm in tool_msgs:
                tool_name = getattr(tm, "name", None) or "tool"
                content = tm.content
                if isinstance(content, str):
                    payload = {"text": content}
                elif isinstance(content, dict):
                    payload = content
                else:
                    payload = {"value": str(content)}
                s.artifacts[tool_name] = payload
                s.working_memory.append({"role": "observation", "content": {"tool": tool_name, "result": payload}})
            # 2) Si venimos del fallback (artifacts ya poblados), también anotar observación
            if s.metadata.get("selected_tool") is None and not tool_msgs and s.artifacts:
                for k, v in s.artifacts.items():
                    s.working_memory.append({"role": "observation", "content": {"tool": k, "result": v}})
            # 3) Subir confianza y marcar listo si hay evidencia
            if tool_msgs or s.artifacts:
                s.confidence = min(1.0, s.confidence + 0.25)
                s.ready_to_answer = True
            return s

    # Construcción del grafo LLM híbrido
    g = StateGraph(State)
    g.add_node("planner", planner_node)
    g.add_node("model", model_node)
    g.add_node("tools", tool_node)
    g.add_node("fallback", fallback_node)  # <-- nuevo
    g.add_node("sync", sync_evidence_node) # <-- nuevo
    g.add_node("critic", critic_node)
    g.add_node("finalizer", finalizer_node)

    g.set_entry_point("planner")
    g.add_edge("planner", "model")

    # Router del modelo: tools (si tool_calls), fallback (si prompt lo pide), o cerrar a sync
    g.add_conditional_edges("model", model_router, {
        "tools": "tools",
        "fallback": "fallback",
        "__end__": "sync",
    })

    # Tras ejecutar tools por ToolNode: una vuelta a model; luego router mandará a sync
    g.add_edge("tools", "model")

    # Tras fallback determinístico: ir a sync
    g.add_edge("fallback", "sync")

    # Sincroniza evidencia → crítico → final
    g.add_edge("sync", "critic")
    g.add_conditional_edges("critic", lambda s: "finalizer", {"finalizer": "finalizer"})
    g.set_finish_point("finalizer")
    return g.compile()


def compile_graph(selector_mode: str = "static"):
    """Compila el grafo según el modo de selección de tools.

    Args:
      selector_mode: "static" (por defecto) o "llm".

    Returns:
      Grafo compilado invocable con `.invoke(state, config=...)`.
    """
    if selector_mode == "llm":
        return _compile_llm()
    return _compile_static()
