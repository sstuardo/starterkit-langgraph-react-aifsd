# tests/test_llm_fallback.py
import os
import pytest
from src.adapters.langgraph_builder import compile_graph
from src.core.state import State
from src.react.register_tools import ensure_tools_registered

pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="requiere OPENAI_API_KEY para modo LLM"
)

def test_llm_fallback_echo():
    ensure_tools_registered()
    graph = compile_graph(selector_mode="llm")
    prompt = "Usa la herramienta echo para repetir exactamente: Hola desde LLM"
    out = graph.invoke(State(user_query=prompt), config={"recursion_limit": 64})
    assert "echo" in out["artifacts"]
