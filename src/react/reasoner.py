"""Nodo Reasoner: decide si pensar más, actuar o finalizar."""
from src.core.state import State
from src.core.observability import span


def should_answer(s: State) -> bool:
    """Criterios de parada: listo, agotado, o confianza suficiente."""
    if s.ready_to_answer:
        return True
    if s.step >= s.max_steps:
        return True
    return s.confidence >= 0.6


def reasoner_node(state: State) -> State:
    """Agrega un Thought y avanza el contador de paso.

    Notas:
      - En grafo compilado no usamos `state.next_step()`, por eso incrementamos aquí.

    Args:
      state: Estado actual.

    Returns:
      Copia del estado con `step` incrementado y posible `ready_to_answer`.
    """
    with span("reasoner", step=state.step):
        s = state.model_copy(deep=True)
        s.step += 1  # importante para cortar ciclos y respetar presupuesto
        s.working_memory.append({
            "role": "thought",
            "content": {"goal": "Acercarse a respuesta verificable", "next": "Elegir tool o cerrar respuesta"},
        })
        if should_answer(s):
            s.ready_to_answer = True
        return s
