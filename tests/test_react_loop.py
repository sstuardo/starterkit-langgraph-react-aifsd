"""Smoke test del loop ReAct puro."""

from src.react.loop import run_react_episode


def test_react_completes_minimally():
    state = run_react_episode("Hola mundo", max_steps=2)
    assert state.ready_to_answer or state.step >= 2
    assert any(msg["role"] == "final" for msg in state.working_memory)
