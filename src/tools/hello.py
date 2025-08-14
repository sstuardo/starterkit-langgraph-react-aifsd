"""
Herramienta `hello`.

Propósito:
  Herramienta de demostración que saluda al usuario.
  Útil para probar el sistema de herramientas y verificar que funciona
  correctamente.
"""

from src.core.tool_interface import ToolInput, ToolOutput


class HelloIn(ToolInput):
    """
    Entrada para la herramienta Hello.

    Propósito:
      Estructurar el nombre del usuario para el saludo.

    Atributos:
      name: Nombre de la persona a saludar.
    """

    name: str = "World"


class HelloTool:
    """Tool de saludo simple para pruebas.

    Propósito:
      Saludar al usuario con un mensaje personalizado.

    Atributos:
      name: Nombre canónico de la tool.
      description: Descripción corta del comportamiento de la tool.
      input_schema: Esquema Pydantic esperado como entrada (`HelloIn`).
      output_schema: Esquema Pydantic producido como salida (`ToolOutput`).
      timeout_s: Tiempo máximo de ejecución sugerido en segundos.
    """

    name: str = "hello"
    description: str = "Saluda al usuario con un mensaje personalizado."
    input_schema = HelloIn
    output_schema = ToolOutput
    timeout_s: int = 1

    def __call__(self, args: HelloIn) -> ToolOutput:
        """Ejecuta la herramienta Hello.

        Propósito:
          Retornar un `ToolOutput` exitoso con un saludo personalizado.

        Args:
          args: Parámetros tipados de entrada (`HelloIn`), incluyendo el
                campo `name`.

        Returns:
          ToolOutput: Objeto con `ok=True` y `content={"greeting": <saludo>}`.
        """
        greeting = f"¡Hola {args.name}! Bienvenido al Starter Kit de ReAct + LangGraph."
        return ToolOutput(ok=True, content={"greeting": greeting})
