"""Crítico: checks ligeros de consistencia y decisión de revisión."""

from src.core.observability import span
from src.core.state import State


def critic_node(state: State) -> State:
    """Marca revise=True si no hay evidencia y hay múltiples errores."""
    with span("critic", step=state.step):
        s = state.model_copy(deep=True)
        has_artifacts = len(s.artifacts) > 0
        many_errors = len(s.errors) >= 2
        need_revision = (not has_artifacts) and many_errors
        s.metadata["revise"] = need_revision
        if not need_revision:
            s.confidence = max(s.confidence, 0.7)
        return s
