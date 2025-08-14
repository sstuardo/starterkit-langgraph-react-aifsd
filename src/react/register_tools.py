"""Registro de herramientas demo para smoke tests."""

from src.react.tool_executor import TOOL_REGISTRY
from src.tools.echo import EchoTool
from src.tools.hello import HelloTool


def ensure_tools_registered() -> None:
    """Registra herramientas de ejemplo en el TOOL_REGISTRY."""
    if "echo" not in TOOL_REGISTRY:
        TOOL_REGISTRY["echo"] = EchoTool()
    if "hello" not in TOOL_REGISTRY:
        TOOL_REGISTRY["hello"] = HelloTool()
