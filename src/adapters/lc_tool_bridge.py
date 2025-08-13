"""
Bridge para convertir tus tools (TOOL_REGISTRY) a StructuredTool (LangChain).
"""
from typing import Dict, List
from langchain_core.tools import StructuredTool
from src.core.tool_interface import Tool

def to_structured_tools(registry: Dict[str, Tool]) -> List[StructuredTool]:
    lc_tools: List[StructuredTool] = []
    for name, tool in registry.items():
        def _callable(**kwargs):
            args = tool.input_schema(**kwargs)  # valida con Pydantic
            out = tool(args)
            return out.content
        st = StructuredTool.from_function(
            func=_callable,
            name=name,
            description=getattr(tool, "description", name),
            args_schema=tool.input_schema,
        )
        lc_tools.append(st)
    return lc_tools
