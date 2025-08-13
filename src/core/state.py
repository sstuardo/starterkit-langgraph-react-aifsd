"""Contrato de estado (State).

Propósito:
  Definir el contenedor tipado que fluye entre nodos del grafo ReAct/LangGraph.
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class State(BaseModel):
    """Estado global que comparten los nodos del grafo."""
    user_query: str
    context: Dict[str, Any] = Field(default_factory=dict)
    working_memory: List[Dict[str, Any]] = Field(default_factory=list)  # [{role, content, meta}]
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    route: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    step: int = 0
    max_steps: int = 6
    confidence: float = 0.0
    ready_to_answer: bool = False
    messages: List[Any] = Field(default_factory=list)  # para ToolNode/tools_condition

    def next_step(self) -> "State":
        """Devuelve una copia del estado avanzando el contador de paso."""
        copy = self.model_copy(deep=True)
        copy.step += 1
        return copy
