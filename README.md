# Starter Kit — ReAct + LangGraph (neutro)

Plantilla mínima y extensible para construir agentes con ciclo **ReAct** y grafo en **LangGraph**, sin sesgos, con rutas **estática** y **LLM** conmutables.

Repo: https://github.com/sstuardo/starterkit-langgraph-react-aifsd/

## Requisitos
- Python **3.11.x** (probado en macOS).
- `pip>=25` recomendado.
- (Opcional) Clave `OPENAI_API_KEY` si usas el modo **LLM**.

## Instalación rápida
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e '.[test]'        # deps base + tests
# Opcional (modo LLM)
pip install -e '.[agent]'
cp .env.example .env            # y completa OPENAI_API_KEY si usarás LLM
```

## Estructura
```
src/
  core/            # State, settings (.env), policies, observabilidad
  react/           # planner, reasoner, tool_selector, tool_executor, critic, finalizer
  adapters/        # langgraph_builder (compila grafo) y graph_entry (entrypoint)
  tools/           # herramientas (p.ej., echo)
tests/             # pruebas básicas
```

## Uso
### 1) Modo estático (router determinístico)
```bash
python -m src.adapters.graph_entry static "Usa echo con el texto: Hola estático"
```
Esperado: `Artifacts: ['echo']` y `evidence_keys` con `echo`.

### 2) Modo LLM (ToolNode + tools_condition)
Requiere `.env` con `OPENAI_API_KEY` y extras `[agent]`.
```bash
python -m src.adapters.graph_entry llm "Usa la herramienta echo para repetir exactamente: Hola desde LLM"
```

**Opciones de control**:
- `LLM_FALLBACK=0|1` (default **1**): si es 1, hay *fallback* determinístico a `echo` cuando el prompt lo pide explícitamente.
- `LLM_TOOL_CHOICE=auto|none|required|<nombre_tool>`: fuerza el uso de tools por el modelo (p.ej. `required` o `echo`).

Ejemplos:
```bash
LLM_FALLBACK=0 LLM_TOOL_CHOICE=required \
python -m src.adapters.graph_entry llm "Usa la herramienta echo ..."
```

### 3) Loop ReAct puro (sin LangGraph)
```bash
python -m src.react.loop
```

## Variables de entorno (`.env`)
- `OPENAI_API_KEY=...` (modo LLM)
- `LLM_MODEL=gpt-4o-mini` (opcional)
- `LLM_TOOL_CHOICE=auto` (opcional)
- `LLM_FALLBACK=1` (opcional)

## Tests
```bash
pytest -q
```
> Si ves warnings de Pydantic/ LangGraph, son inofensivos. Puedes silenciarlos con `tests/conftest.py` (ver docs).

## Solución de problemas
Consulta **docs/TROUBLESHOOTING.md** para errores comunes como `GraphRecursionError` o `Invalid parameter: messages with role 'tool' ...`

## Versionado
- SemVer en `CHANGELOG.md`.
- Rango de dependencias seguro en `pyproject.toml`.

## Licencia
MIT — ver `LICENSE`.
