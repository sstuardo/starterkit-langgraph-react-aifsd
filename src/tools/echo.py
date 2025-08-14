"""
Herramienta `echo`.

Propósito:
  Proveer una tool de demostración que devuelve exactamente el mismo texto de
  entrada. Útil para probar el pipeline de Tools en el ciclo ReAct
  (selección, ejecución y observación) sin depender de servicios externos.

Notas:
  - Registrar esta tool en el `TOOL_REGISTRY` antes de usarla
    (ver `src/react/register_tools.py`).
  - Contratos tipados con Pydantic a través de `ToolInput` y `ToolOutput`.
"""

from src.core.tool_interface import ToolInput, ToolOutput


class EchoIn(ToolInput):
    """
    Entrada para la herramienta Echo.

    Propósito:
      Estructurar el texto de entrada que será devuelto por la herramienta.

    Atributos:
      text: Texto a reflejar en la salida.
    """

    text: str = ""


class EchoTool:
    """Tool de eco simple para pruebas.

    Propósito:
      Devolver el mismo contenido recibido en `EchoIn.text` para verificar
      la correcta orquestación de llamadas a herramientas.

    Atributos:
      name: Nombre canónico de la tool.
      description: Descripción corta del comportamiento de la tool.
      input_schema: Esquema Pydantic esperado como entrada (`EchoIn`).
      output_schema: Esquema Pydantic producido como salida (`ToolOutput`).
      timeout_s: Tiempo máximo de ejecución sugerido en segundos.
    """

    name: str = "echo"
    description: str = "Devuelve el mismo texto de entrada."
    input_schema = EchoIn
    output_schema = ToolOutput
    timeout_s: int = 2

    def __call__(self, args: EchoIn) -> ToolOutput:
        """Ejecuta la herramienta Echo.

        Propósito:
          Retornar un `ToolOutput` exitoso que contiene el mismo texto
          recibido en `args.text`.

        Args:
          args: Parámetros tipados de entrada (`EchoIn`), incluyendo el
                campo `text`.

        Returns:
          ToolOutput: Objeto con `ok=True` y `content={"echo": <texto>}`.

        Raises:
          (No se esperan excepciones en el flujo normal).
        """
        return ToolOutput(ok=True, content={"echo": args.text})
