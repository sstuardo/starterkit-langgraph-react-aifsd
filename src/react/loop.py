"""Episodio ReAct 'puro' (sin LangGraph) para pruebas rápidas.

Propósito:
  Ejecutar el ciclo ReAct con el selector estático y ver artifacts (echo) sin
  necesidad de compilar el grafo.
"""

from src.core.observability import span
from src.core.policies import DEFAULT_BUDGET
from src.core.settings import load_settings
from src.core.state import State
from src.react.critic import critic_node
from src.react.finalizer import finalizer_node
from src.react.planner import planner_node
from src.react.reasoner import reasoner_node  # incrementa s.step internamente
from src.react.register_tools import ensure_tools_registered
from src.react.tool_executor import tool_executor_node
from src.react.tool_selector import tool_selector_node


def run_react_episode(user_query: str, max_steps: int | None = None) -> State:
    """Ejecuta un episodio ReAct (planner → reasoner → tools? → critic → final).

    Notas:
      - NO usamos s.next_step(): reasoner_node incrementa s.step internamente.
      - El selector estático forzará 'echo' en la primera pasada (step==1).
    """
    ensure_tools_registered()
    s = State(user_query=user_query)
    s.max_steps = max_steps or DEFAULT_BUDGET.max_steps

    with span("react_episode", query=user_query):
        s = planner_node(s)

        while True:
            s = reasoner_node(s)  # <-- incrementa step
            if s.ready_to_answer or s.step >= s.max_steps:
                break

            s = tool_selector_node(s)
            if s.metadata.get("selected_tool"):
                s = tool_executor_node(s)
            else:
                # Sin tool seleccionada, corta el ciclo para ir a critic
                break

        s = critic_node(s)
        if (
            s.metadata.get("revise", False)
            and not s.metadata.get("revised", False)
            and s.step < s.max_steps
        ):
            s.metadata["revised"] = True
            s = reasoner_node(s)
        s = finalizer_node(s)
        return s


if __name__ == "__main__":
    load_settings()  # lee .env (OPENAI_API_KEY si luego usas modo LLM)
    out = run_react_episode("Demo loop estático: usa echo una vez.")
    final = out.working_memory[-1]["content"] if out.working_memory else {}
    print("=== FINAL (loop) ===")
    print(final)
    print("Artifacts:", list(out.artifacts.keys()))
    print("Errors:", out.errors[-3:])
    print("Confidence:", out.confidence)
