"""Nodo Planner: bosqueja plan de alto nivel para el episodio ReAct."""
from src.core.state import State
from src.core.observability import span

def planner_node(state: State) -> State:
    """Escribe un plan inicial en working_memory (no ejecuta tools)."""
    with span("planner"):
        plan = [
            "Clarificar objetivo si es ambiguo",
            "Identificar si se requiere tool (retrieval/web/vision)",
            "Ejecutar tool si aporta evidencia",
            "Sintetizar y verificar",
        ]
        s = state.model_copy(deep=True)
        s.working_memory.append({"role": "planner", "content": {"plan": plan}})
        return s
