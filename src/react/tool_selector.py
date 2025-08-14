"""Selector de herramienta: decide qué tool (si alguna) conviene usar ahora.

Propósito:
  Determinar de forma determinística si conviene ejecutar una tool.
  En la primera pasada, fuerza 'echo' para obtener un artifact y evitar loops.
"""

from src.core.observability import span
from src.core.state import State


def tool_selector_node(state: State) -> State:
    """Escribe en `metadata['selected_tool']` el nombre de la tool o `None`.

    Reglas:
      - Si `step == 1` (primera pasada tras reasoner) → seleccionar 'echo'.
      - Si la consulta contiene ciertos patrones → seleccionar tool específica.
      - En otro caso → `None` para ir a `critic`.
    """
    with span("tool_selector", step=state.step):
        s = state.model_copy(deep=True)

        # Forzar 'echo' SOLO en la primera vuelta
        if s.step == 1:
            s.metadata["selected_tool"] = "echo"
            return s

        query = s.user_query.lower()
        if any(k in query for k in ["documento", "pdf", "imagen", "tabla"]):
            s.metadata["selected_tool"] = "vision_extract"
        elif any(k in query for k in ["cita", "fuente", "web", "buscar"]):
            s.metadata["selected_tool"] = "web_search"
        elif any(k in query for k in ["base", "conocimiento", "vector", "faq"]):
            s.metadata["selected_tool"] = "vector_lookup"
        else:
            s.metadata["selected_tool"] = None
        return s
