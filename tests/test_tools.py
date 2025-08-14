"""Contrato mínimo de ToolOutput."""

from src.core.tool_interface import ToolOutput


def test_tool_output_contract():
    out = ToolOutput(ok=True, content={"k": "v"})
    assert out.ok and isinstance(out.content, dict)
