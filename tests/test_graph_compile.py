"""Smoke test del grafo LangGraph compilado (modo estático por defecto)."""

from src.adapters.langgraph_builder import compile_graph
from src.core.state import State
from src.react.register_tools import ensure_tools_registered


def test_graph_compiles_and_runs():
    ensure_tools_registered()
    graph = compile_graph()
    # LangGraph retorna un dict; reconstruimos State para asserts tipados
    result_dict = graph.invoke(State(user_query="Ping"), config={"recursion_limit": 50})
    final_state = State(**result_dict)

    assert final_state.working_memory, "working_memory vacío"
    # Último bloque debe ser 'final' (lo agrega finalizer_node)
    last = final_state.working_memory[-1]
    assert isinstance(last, dict) and last.get("role") == "final"
