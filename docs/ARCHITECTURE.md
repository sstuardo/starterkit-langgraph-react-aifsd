# Arquitectura

## Propósito
Proveer un arquetipo neutral para agentes **ReAct** con dos modos:
- **Estático**: enrutado determinístico (útil para tests, baja latencia).
- **LLM**: selección de herramientas vía `ToolNode + tools_condition` con guardas anti-loop y *fallback* opcional.

## Componentes

### `State` (Pydantic)
Campos principales: `user_query`, `working_memory`, `artifacts`, `errors`, `confidence`, `step`, `max_steps`, `metadata`, `messages` (para modo LLM).

### Nodos ReAct
- `planner`: inicializa el episodio.
- `reasoner`: incrementa `step` y decide si seguir o cerrar.
- `tool_selector`: determina tool en modo estático (fuerza `echo` en la 1ª pasada).
- `tool_executor`: invoca la tool seleccionada y limpia la selección.
- `critic`: bloque de revisión simple.
- `finalizer`: llena el bloque final (summary + evidence_keys + confianza).

### Builder de LangGraph
- **Estático**: `planner → reasoner → tool_selector? → tool_executor? → reasoner → critic → finalizer`.
- **LLM**: `planner → model → (tools?) → model → sync → critic → finalizer`.
  - `model`: inicializa primer turno (System + Human), no borra `ToolMessage`, incrementa `step`.
  - `model_router`: cierra si hay `ToolMessage` o se agotan pasos; si el prompt pide `echo` y `LLM_FALLBACK=1`, va a `fallback`.
  - `fallback`: ejecuta determinísticamente `echo` (una pasada) y marca `ready_to_answer`.
  - `sync`: copia resultados de herramientas (ToolMessage/artifacts) a `working_memory`, sube `confidence` y marca listo.

### Tools
- `echo`: tool de “cálculo puro” (sin I/O), ideal para pruebas. Interfaz propia (`ToolInput`, `ToolOutput`).
- `TOOL_REGISTRY` + `ensure_tools_registered()` para añadir herramientas.

### Observabilidad
- `structlog` con spans (`span("node", ...)`) para tiempos y debugging.

## Puntos de extensión
- Añadir nuevas tools en `src/tools/` y registrarlas.
- Cambiar reglas de `tool_selector` (estático) o `SYSTEM_HINT` (LLM).
- Ajustar `model_router` para permitir múltiples tool-calls.
- Sustituir `ChatOpenAI` por otro proveedor compatible.

## Seguridad / AIFSD (resumen)
- Prompts neutros, sin sesgos, y políticas de salida claras.
- No exponer claves ni PII; usar `.env` y validaciones.
- Limitar pasos y tool-calls para evitar comportamientos no controlados.
