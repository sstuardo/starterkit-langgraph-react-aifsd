"""Sistema avanzado de observabilidad para agentes ReAct + LangGraph.

Características:
- Métricas de rendimiento (P50/P95 latencia)
- Trazabilidad con correlation IDs
- Métricas de costo y tokens
- Dashboard de KPIs
- Alertas y SLOs
"""

import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from collections import defaultdict
import statistics

import structlog

# Configuración de logging estructurado
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

log = structlog.get_logger()


@dataclass
class Metrics:
    """Métricas de rendimiento y costo del agente."""
    
    # Latencia
    latency_p50: float = 0.0
    latency_p95: float = 0.0
    latency_p99: float = 0.0
    
    # Tokens y costo
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    
    # Rendimiento
    total_steps: int = 0
    successful_steps: int = 0
    failed_steps: int = 0
    tool_calls: int = 0
    tool_success_rate: float = 0.0
    
    # Errores
    error_count: int = 0
    error_rate: float = 0.0
    
    # Recursos
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0


@dataclass
class TraceContext:
    """Contexto de trazabilidad para correlacionar logs y métricas."""
    
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    span_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_span_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    
    def new_span(self) -> 'TraceContext':
        """Crea un nuevo span hijo."""
        return TraceContext(
            trace_id=self.trace_id,
            span_id=str(uuid.uuid4()),
            parent_span_id=self.span_id,
            user_id=self.user_id,
            session_id=self.session_id,
            request_id=self.request_id
        )


class MetricsCollector:
    """Recolector centralizado de métricas."""
    
    def __init__(self):
        self.metrics: Dict[str, Metrics] = defaultdict(Metrics)
        self.latency_samples: Dict[str, List[float]] = defaultdict(list)
        self.error_samples: Dict[str, List[str]] = defaultdict(list)
        self._lock = None  # Para futura implementación de thread-safety
    
    def record_latency(self, operation: str, latency_ms: float):
        """Registra latencia de una operación."""
        self.latency_samples[operation].append(latency_ms)
        
        # Calcular percentiles
        if len(self.latency_samples[operation]) >= 10:  # Mínimo de muestras
            samples = self.latency_samples[operation]
            self.metrics[operation].latency_p50 = statistics.median(samples)
            self.metrics[operation].latency_p95 = statistics.quantiles(samples, n=20)[18]  # P95
            self.metrics[operation].latency_p99 = statistics.quantiles(samples, n=100)[98]  # P99
    
    def record_tokens(self, operation: str, input_tokens: int, output_tokens: int):
        """Registra uso de tokens."""
        metrics = self.metrics[operation]
        metrics.input_tokens += input_tokens
        metrics.output_tokens += output_tokens
        metrics.total_tokens += input_tokens + output_tokens
        
        # Estimación de costo (aproximada para OpenAI)
        # GPT-4: $0.03/1K input, $0.06/1K output
        input_cost = (input_tokens / 1000) * 0.03
        output_cost = (output_tokens / 1000) * 0.06
        metrics.estimated_cost_usd += input_cost + output_cost
    
    def record_step(self, operation: str, success: bool, tool_call: bool = False):
        """Registra un paso de ejecución."""
        metrics = self.metrics[operation]
        metrics.total_steps += 1
        
        if success:
            metrics.successful_steps += 1
        else:
            metrics.failed_steps += 1
            metrics.error_count += 1
        
        if tool_call:
            metrics.tool_calls += 1
        
        # Calcular tasas
        if metrics.total_steps > 0:
            metrics.tool_success_rate = metrics.successful_steps / metrics.total_steps
            metrics.error_rate = metrics.error_count / metrics.total_steps
    
    def get_summary(self, operation: str = None) -> Dict[str, Any]:
        """Obtiene resumen de métricas."""
        if operation:
            return {
                "operation": operation,
                "metrics": self.metrics[operation].__dict__
            }
        
        # Resumen global
        global_metrics = Metrics()
        for op_metrics in self.metrics.values():
            global_metrics.total_steps += op_metrics.total_steps
            global_metrics.total_tokens += op_metrics.total_tokens
            global_metrics.estimated_cost_usd += op_metrics.estimated_cost_usd
            global_metrics.error_count += op_metrics.error_count
        
        if global_metrics.total_steps > 0:
            global_metrics.error_rate = global_metrics.error_count / global_metrics.total_steps
        
        return {
            "global_metrics": global_metrics.__dict__,
            "operations": {op: metrics.__dict__ for op, metrics in self.metrics.items()}
        }


# Instancia global del recolector
metrics_collector = MetricsCollector()


@contextmanager
def span(name: str, trace_context: Optional[TraceContext] = None, **kv):
    """Crea un bloque con métricas avanzadas, trazabilidad y logging estructurado."""
    
    if trace_context is None:
        trace_context = TraceContext()
    
    span_context = trace_context.new_span()
    t0 = time.time()
    
    # Log de inicio con contexto de trazabilidad
    log.info(
        "span.start",
        name=name,
        trace_id=span_context.trace_id,
        span_id=span_context.span_id,
        parent_span_id=span_context.parent_span_id,
        **kv
    )
    
    try:
        yield span_context
        
        # Métricas de éxito
        dt = (time.time() - t0) * 1000  # Convertir a ms
        metrics_collector.record_latency(name, dt)
        metrics_collector.record_step(name, success=True)
        
        log.info(
            "span.end",
            name=name,
            trace_id=span_context.trace_id,
            span_id=span_context.span_id,
            elapsed_ms=dt,
            **kv
        )
        
    except Exception as e:
        # Métricas de error
        dt = (time.time() - t0) * 1000
        metrics_collector.record_latency(name, dt)
        metrics_collector.record_step(name, success=False)
        
        log.error(
            "span.error",
            name=name,
            trace_id=span_context.trace_id,
            span_id=span_context.span_id,
            elapsed_ms=dt,
            error=str(e),
            error_type=type(e).__name__,
            **kv
        )
        raise


def get_metrics_summary() -> Dict[str, Any]:
    """Obtiene resumen completo de métricas."""
    return metrics_collector.get_summary()


def reset_metrics():
    """Resetea todas las métricas (útil para tests)."""
    global metrics_collector
    metrics_collector = MetricsCollector()


# Decorador para métricas automáticas
def track_metrics(operation_name: str = None):
    """Decorador para tracking automático de métricas."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            op_name = operation_name or func.__name__
            
            with span(op_name) as span_ctx:
                # Agregar contexto de trazabilidad a la función
                if hasattr(func, '__self__') and hasattr(func.__self__, 'trace_context'):
                    func.__self__.trace_context = span_ctx
                
                result = func(*args, **kwargs)
                return result
        
        return wrapper
    return decorator
