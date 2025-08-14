"""Contrato de estado (State).

Propósito:
  Definir el contenedor tipado que fluye entre nodos del grafo ReAct/LangGraph.
"""

from typing import Any

from pydantic import BaseModel, Field


class State(BaseModel):
    """Estado global que comparten los nodos del grafo."""

    user_query: str
    context: dict[str, Any] = Field(default_factory=dict)
    working_memory: list[dict[str, Any]] = Field(
        default_factory=list
    )  # [{role, content, meta}]
    artifacts: dict[str, Any] = Field(default_factory=dict)
    route: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    step: int = 0
    max_steps: int = 6
    confidence: float = 0.0
    ready_to_answer: bool = False
    messages: list[Any] = Field(default_factory=list)  # para ToolNode/tools_condition

    def next_step(self) -> "State":
        """Devuelve una copia del estado avanzando el contador de paso."""
        copy = self.model_copy(deep=True)
        copy.step += 1
        return copy
