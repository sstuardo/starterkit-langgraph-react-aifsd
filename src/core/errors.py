"""Errores de tools (clasificación básica)."""


class RecoverableToolError(Exception):
    """Error recuperable (reintento posible)."""

    ...


class TerminalToolError(Exception):
    """Error terminal (cortar ruta o degradar)."""

    ...
