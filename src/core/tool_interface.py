"""Contratos para herramientas (tools)."""

from typing import Protocol

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
    input_schema: type[ToolInput]
    output_schema: type[ToolOutput]
    timeout_s: int

    def __call__(self, args: ToolInput) -> ToolOutput: ...
