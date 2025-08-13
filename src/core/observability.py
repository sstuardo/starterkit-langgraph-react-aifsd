"""Observabilidad mínima con spans y structlog."""
import time, structlog
from contextlib import contextmanager

log = structlog.get_logger()

@contextmanager
def span(name: str, **kv):
    """Crea un bloque con log de inicio/fin/error y tiempo transcurrido."""
    t0 = time.time()
    try:
        log.info("span.start", name=name, **kv)
        yield
        dt = time.time() - t0
        log.info("span.end", name=name, elapsed_s=dt, **kv)
    except Exception as e:
        dt = time.time() - t0
        log.error("span.error", name=name, elapsed_s=dt, error=str(e), **kv)
        raise
