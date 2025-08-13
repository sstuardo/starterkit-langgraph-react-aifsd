"""Políticas de presupuesto (pasos, tokens, latencia)."""
from pydantic import BaseModel

class BudgetPolicy(BaseModel):
    """Límites por episodio."""
    max_steps: int = 6
    max_latency_s: float | None = None
    max_tokens: int | None = None
    min_confidence_for_answer: float = 0.6

DEFAULT_BUDGET = BudgetPolicy()
