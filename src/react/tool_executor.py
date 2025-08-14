"""Ejecutor de herramientas: invoca la tool seleccionada y registra observación."""

from src.core.observability import span
from src.core.state import State
from src.core.tool_interface import Tool, ToolInput, ToolOutput

TOOL_REGISTRY: dict[str, Tool] = {}


def _build_args_for_tool(tool: Tool, state: State) -> ToolInput:
    """Mapea campos comunes desde State hacia el input_schema de la tool."""
    schema = tool.input_schema
    data = {}
    fields = getattr(schema, "model_fields", {}) or {}
    if "query" in fields:
        data["query"] = state.user_query
    if "text" in fields:
        data["text"] = state.user_query
    try:
        return schema(**data)  # type: ignore
    except Exception:
        return schema()  # fallback vacío


def tool_executor_node(state: State) -> State:
    """Invoca la tool de `metadata['selected_tool']` y guarda artifacts/observations.

    Limpia `selected_tool` al final para evitar re-ejecuciones consecutivas.
    """
    tool_name = state.metadata.get("selected_tool")
    with span("tool_executor", tool=tool_name, step=state.step):
        s = state.model_copy(deep=True)
        if not tool_name:
            s.working_memory.append(
                {
                    "role": "observation",
                    "content": "No tool selected; continue reasoning",
                }
            )
            return s

        tool = TOOL_REGISTRY.get(tool_name)
        if not tool:
            s.errors.append({"tool": tool_name, "error": "Tool not registered"})
            s.working_memory.append(
                {"role": "observation", "content": f"{tool_name} not available"}
            )
            return s

        args = _build_args_for_tool(tool, s)
        out: ToolOutput = tool(args)  # type: ignore
        if out.ok:
            s.artifacts[tool_name] = out.content
            s.working_memory.append(
                {"role": "observation", "content": f"{tool_name} ok"}
            )
            s.confidence = min(1.0, s.confidence + 0.25)
        else:
            s.errors.append({"tool": tool_name, "error": out.error or "unknown"})
            s.working_memory.append(
                {"role": "observation", "content": f"{tool_name} error"}
            )

        # clave: limpiar selección para no re-ejecutar en bucle
        s.metadata.pop("selected_tool", None)
        return s
