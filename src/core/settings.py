"""Carga de configuración y variables de entorno."""

import os

from dotenv import load_dotenv


def load_settings() -> None:
    """Carga .env si existe (sin sobreescribir variables ya definidas)."""
    load_dotenv(override=False)
    _ = os.getenv("OPENAI_API_KEY", None)
