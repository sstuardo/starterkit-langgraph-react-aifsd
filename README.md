# Starter Kit — ReAct + LangGraph

Plantilla neutral para agentes con ciclo ReAct y compilación a grafo con LangGraph.

## Estructura
- `core/`: contratos (`State`), tools (interfaces), políticas, observabilidad, settings (.env).
- `react/`: planner, reasoner, tool_selector, tool_executor, critic, finalizer y loop puro.
- `adapters/`: `langgraph_builder.py` (compila el grafo) y `graph_entry.py` (entrypoint).
- `prompts/`: plantillas ReAct y políticas.
- `tests/`: pruebas de loop y compilación de grafo.

## Uso
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .[test]
cp .env.example .env
make test
make run        # loop puro (sin LangGraph)
make run-graph  # grafo con LangGraph
