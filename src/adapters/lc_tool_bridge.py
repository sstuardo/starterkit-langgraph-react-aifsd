"""
Bridge para convertir tus tools (TOOL_REGISTRY) a StructuredTool (LangChain).
"""

from langchain_core.tools import StructuredTool

from src.core.tool_interface import Tool


def to_structured_tools(registry: dict[str, Tool]) -> list[StructuredTool]:
    lc_tools: list[StructuredTool] = []
    for name, tool in registry.items():

        def make_callable(tool_instance):
            def _callable(**kwargs):
                args = tool_instance.input_schema(**kwargs)  # valida con Pydantic
                out = tool_instance(args)
                return out.content

            return _callable

        st = StructuredTool.from_function(
            func=make_callable(tool),
            name=name,
            description=getattr(tool, "description", name),
            args_schema=tool.input_schema,
        )
        lc_tools.append(st)
    return lc_tools
