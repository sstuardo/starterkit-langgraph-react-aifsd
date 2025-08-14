"""Entry point para ejecutar el grafo con selector parametrizable (estático ↔ LLM).

Propósito:
  - Permitir correr una invocación del grafo en modo "static" (router
    determinístico) o "llm" (ToolNode + tools_condition) usando argumento
    CLI o variable de entorno.
  - Cargar variables desde `.env` (ej. OPENAI_API_KEY) antes de compilar.
  - Imprimir un resumen final (bloque final, artifacts, errores, confianza).

Uso CLI:
  python -m src.adapters.graph_entry
  python -m src.adapters.graph_entry static "Usa echo con el texto: hola"
  python -m src.adapters.graph_entry llm "Usa la herramienta echo para repetir: hola LLM"

Variables de entorno:
  - SELECTOR_MODE: "static" | "llm" (se usa si no pasas el modo por CLI;
    default "static").
  - OPENAI_API_KEY: requerida solo en modo "llm". Se carga desde `.env`
    vía load_settings().
"""

import os
import sys

from src.adapters.langgraph_builder import compile_graph
from src.core.settings import load_settings
from src.core.state import State
from src.react.register_tools import ensure_tools_registered


def main() -> None:
    """Compila el grafo, lo invoca y muestra un resumen final.

    Flujo:
      1) Carga `.env`.
      2) Registra tools demo (p. ej., `echo`).
      3) Lee `mode` y `prompt` desde CLI (si no, desde entorno).
      4) Compila el grafo según `mode`.
      5) Invoca con un `recursion_limit` holgado.
      6) Reconstruye `State` y muestra bloque final, artifacts, errores
         y confianza.
    """
    # 1) Cargar variables de entorno desde .env
    load_settings()

    # 2) Registrar herramientas demo (echo, etc.)
    ensure_tools_registered()

    # 3) Modo y prompt: CLI > entorno > defaults
    args = sys.argv[1:]
    mode = args[0] if args else os.getenv("SELECTOR_MODE", "static")
    prompt = "Demo selector_mode=" + mode
    if len(args) >= 2:
        prompt = " ".join(args[1:])

    # 4) Compilar grafo parametrizado
    graph = compile_graph(selector_mode=mode)

    # 5) Ejecutar con límite de recursión razonable (evita cortes prematuros)
    initial = State(user_query=prompt)
    recursion_limit = max(32, 3 * initial.max_steps + 4)
    result = graph.invoke(initial, config={"recursion_limit": recursion_limit})

    # 6) Reconstruir State y mostrar resumen
    final_state = State(**result)
    last = (
        final_state.working_memory[-1]["content"] if final_state.working_memory else {}
    )

    print("=== FINAL ===")
    print(last)
    print("Artifacts:", list(final_state.artifacts.keys()))
    print("Errors:", final_state.errors[-3:])
    print("Confidence:", final_state.confidence)


if __name__ == "__main__":
    main()
