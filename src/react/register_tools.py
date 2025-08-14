"""Registro de herramientas disponibles para el agente ReAct."""

from src.react.tool_executor import TOOL_REGISTRY
from src.tools.echo import EchoTool
from src.tools.hello import HelloTool
from src.tools.monitor import MonitorTool
from src.tools.budget_monitor import BudgetMonitorTool


def ensure_tools_registered() -> None:
    """Registra herramientas de ejemplo en el TOOL_REGISTRY."""
    if "echo" not in TOOL_REGISTRY:
        TOOL_REGISTRY["echo"] = EchoTool()
    if "hello" not in TOOL_REGISTRY:
        TOOL_REGISTRY["hello"] = HelloTool()
    if "monitor" not in TOOL_REGISTRY:
        TOOL_REGISTRY["monitor"] = MonitorTool()
    if "budget_monitor" not in TOOL_REGISTRY:
        TOOL_REGISTRY["budget_monitor"] = BudgetMonitorTool()
