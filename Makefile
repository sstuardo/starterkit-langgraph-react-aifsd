.PHONY: setup test run run-graph
PY?=python

setup:
	$(PY) -m venv .venv && . .venv/bin/activate && pip install -U pip && pip install -e .[test]

test:
	. .venv/bin/activate && pytest

run:
	. .venv/bin/activate && $(PY) -m src.react.loop

run-graph:
	. .venv/bin/activate && $(PY) -m src.adapters.graph_entry
