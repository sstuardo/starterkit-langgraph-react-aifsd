# src/react/finalizer.py
"""Nodo Finalizer: construye el bloque final homogéneo para ambos modos."""

from src.core.observability import span
from src.core.state import State


def finalizer_node(state: State) -> State:
    with span("finalizer", step=state.step):
        s = state.model_copy(deep=True)
        evidence_keys = sorted(s.artifacts.keys())
        summary = "Respuesta final (plantilla) basada en evidencia disponible."
        s.working_memory.append(
            {
                "role": "final",
                "content": {
                    "summary": summary,
                    "evidence_keys": evidence_keys,
                    "limitations": [],
                    "confidence": s.confidence,
                },
            }
        )
        s.ready_to_answer = True
        return s
