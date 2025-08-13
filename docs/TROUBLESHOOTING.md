# Troubleshooting

## `GraphRecursionError`
- Sube `recursion_limit` al invocar el grafo (`config={"recursion_limit": 50}`).
- Asegura que `reasoner`/`model` incrementen `state.step`.
- En modo LLM, el `model_router` corta tras ver `ToolMessage` o agotar pasos.

## `Invalid parameter: messages with role 'tool'...`
- Primer turno debe iniciar con `SystemMessage` + `HumanMessage` (no `ToolMessage`).
- La función `_prepare_first_turn` limpia `ToolMessage` huérfanos.

## El LLM no llama herramientas
- Usa `LLM_TOOL_CHOICE=required` o `LLM_TOOL_CHOICE=<nombre_tool>`.
- Mantén `LLM_FALLBACK=1` para prompts que piden explícitamente `echo`.

## ImportError / versiones
- `selector_mode="llm"` requiere `langgraph>=0.3.1` y extras `[agent]`.
- Error de pyproject TOML duplicado: mantener **un solo** bloque `[project.optional-dependencies]`.

## zsh: `.[test]` no encontrado
- Usa comillas: `pip install -e '.[test]'`.

## Import circular
- Evita `from src.react.tool_selector import tool_selector_node` dentro del propio `tool_selector.py`.
