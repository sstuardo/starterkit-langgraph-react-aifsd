"""Contratos para herramientas (tools)."""
from typing import Protocol, Type
from pydantic import BaseModel

class ToolInput(BaseModel):
    """Base para inputs tipados de tools."""
    pass

class ToolOutput(BaseModel):
    """Salida estándar de una tool."""
    ok: bool = True
    content: str | dict | list | None = None
    error: str | None = None

class Tool(Protocol):
    """Interfaz de herramientas invocables por el grafo."""
    name: str
    description: str
    input_schema: Type[ToolInput]
    output_schema: Type[ToolOutput]
    timeout_s: int

    def __call__(self, args: ToolInput) -> ToolOutput: ...
