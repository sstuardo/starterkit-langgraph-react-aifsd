"""Tests para el sistema de observabilidad avanzada."""

import pytest
from unittest.mock import patch, MagicMock

from src.core.observability import (
    Metrics, TraceContext, MetricsCollector, span, 
    get_metrics_summary, reset_metrics, track_metrics
)
from src.core.metrics_dashboard import (
    SLODefinition, MetricsDashboard, get_dashboard, 
    update_dashboard, get_kpis
)
from src.tools.monitor import MonitorTool, MonitorIn


class TestMetrics:
    """Tests para la clase Metrics."""
    
    def test_metrics_initialization(self):
        """Test de inicialización de métricas."""
        metrics = Metrics()
        
        assert metrics.latency_p50 == 0.0
        assert metrics.latency_p95 == 0.0
        assert metrics.total_tokens == 0
        assert metrics.estimated_cost_usd == 0.0
        assert metrics.total_steps == 0
        assert metrics.error_count == 0
    
    def test_metrics_custom_values(self):
        """Test de métricas con valores personalizados."""
        metrics = Metrics(
            latency_p50=100.0,
            total_tokens=500,
            total_steps=10
        )
        
        assert metrics.latency_p50 == 100.0
        assert metrics.total_tokens == 500
        assert metrics.total_steps == 10


class TestTraceContext:
    """Tests para la clase TraceContext."""
    
    def test_trace_context_initialization(self):
        """Test de inicialización de contexto de trazabilidad."""
        context = TraceContext()
        
        assert context.trace_id is not None
        assert context.span_id is not None
        assert context.parent_span_id is None
        assert context.user_id is None
    
    def test_new_span(self):
        """Test de creación de nuevo span hijo."""
        parent = TraceContext()
        child = parent.new_span()
        
        assert child.trace_id == parent.trace_id
        assert child.span_id != parent.span_id
        assert child.parent_span_id == parent.span_id


class TestMetricsCollector:
    """Tests para la clase MetricsCollector."""
    
    def test_metrics_collector_initialization(self):
        """Test de inicialización del recolector."""
        collector = MetricsCollector()
        
        assert len(collector.metrics) == 0
        assert len(collector.latency_samples) == 0
    
    def test_record_latency(self):
        """Test de registro de latencia."""
        collector = MetricsCollector()
        
        # Agregar muestras para calcular percentiles
        for i in range(20):
            collector.record_latency("test_op", float(i))
        
        metrics = collector.metrics["test_op"]
        assert metrics.latency_p50 > 0
        assert metrics.latency_p95 > 0
    
    def test_record_tokens(self):
        """Test de registro de tokens."""
        collector = MetricsCollector()
        
        collector.record_tokens("test_op", 100, 50)
        
        metrics = collector.metrics["test_op"]
        assert metrics.input_tokens == 100
        assert metrics.output_tokens == 50
        assert metrics.total_tokens == 150
        assert metrics.estimated_cost_usd > 0
    
    def test_record_step(self):
        """Test de registro de pasos."""
        collector = MetricsCollector()
        
        collector.record_step("test_op", success=True, tool_call=True)
        collector.record_step("test_op", success=False, tool_call=False)
        
        metrics = collector.metrics["test_op"]
        assert metrics.total_steps == 2
        assert metrics.successful_steps == 1
        assert metrics.failed_steps == 1
        assert metrics.tool_calls == 1
        assert metrics.tool_success_rate == 0.5
        assert metrics.error_rate == 0.5


class TestSpan:
    """Tests para la función span."""
    
    def test_span_success(self):
        """Test de span exitoso."""
        with span("test_span") as span_ctx:
            assert span_ctx.trace_id is not None
            assert span_ctx.span_id is not None
        
        # Verificar que se registraron métricas
        summary = get_metrics_summary()
        assert "test_span" in summary["operations"]
    
    def test_span_with_exception(self):
        """Test de span con excepción."""
        with pytest.raises(ValueError):
            with span("test_span_error"):
                raise ValueError("Test error")
        
        # Verificar que se registraron métricas de error
        summary = get_metrics_summary()
        assert "test_span_error" in summary["operations"]
        assert summary["operations"]["test_span_error"]["error_count"] > 0


class TestSLODefinition:
    """Tests para la clase SLODefinition."""
    
    def test_slo_evaluation(self):
        """Test de evaluación de SLOs."""
        # SLO de latencia <= 100ms
        slo = SLODefinition("latency_test", "latency", 100.0, "<=")
        
        assert slo.evaluate(50.0) == True   # Cumple
        assert slo.evaluate(100.0) == True  # Cumple exactamente
        assert slo.evaluate(150.0) == False # No cumple
    
    def test_slo_operators(self):
        """Test de diferentes operadores de SLO."""
        slo_ge = SLODefinition("test", "metric", 0.95, ">=")
        slo_eq = SLODefinition("test", "metric", 1.0, "==")
        slo_ne = SLODefinition("test", "metric", 0.0, "!=")
        
        assert slo_ge.evaluate(0.98) == True
        assert slo_eq.evaluate(1.0) == True
        assert slo_ne.evaluate(0.5) == True


class TestMetricsDashboard:
    """Tests para la clase MetricsDashboard."""
    
    def test_dashboard_initialization(self):
        """Test de inicialización del dashboard."""
        dashboard = MetricsDashboard()
        
        assert len(dashboard.slos) > 0  # SLOs por defecto
        assert len(dashboard.alerts) == 0
        assert len(dashboard.metrics_history) == 0
    
    def test_add_slo(self):
        """Test de agregar SLO personalizado."""
        dashboard = MetricsDashboard()
        initial_count = len(dashboard.slos)
        
        dashboard.add_slo(
            "custom_slo", "custom_metric", 0.9, ">=", 
            "warning", "Test SLO"
        )
        
        assert len(dashboard.slos) == initial_count + 1
    
    def test_slo_evaluation(self):
        """Test de evaluación de SLOs."""
        dashboard = MetricsDashboard()
        
        # Simular métricas que violan SLOs
        with patch('src.core.metrics_dashboard.get_metrics_summary') as mock_metrics:
            mock_metrics.return_value = {
                "global_metrics": {
                    "latency_p95": 6000.0,  # Viola SLO de 5s
                    "tool_success_rate": 0.85,  # Viola SLO de 95%
                    "error_rate": 0.15,  # Viola SLO de 5%
                    "total_tokens": 1500  # Viola SLO de 1000
                },
                "operations": {}
            }
            
            violations = dashboard.evaluate_slos(mock_metrics.return_value)
            assert len(violations) > 0


class TestMonitorTool:
    """Tests para la herramienta Monitor."""
    
    def test_monitor_tool_initialization(self):
        """Test de inicialización de la herramienta."""
        tool = MonitorTool()
        
        assert tool.name == "monitor"
        assert tool.description is not None
        assert tool.timeout_s == 5
    
    def test_monitor_kpis_action(self):
        """Test de acción KPIs."""
        tool = MonitorTool()
        args = MonitorIn(action="kpis")
        
        result = tool(args)
        
        assert result.ok == True
        assert "performance" in result.content
        assert "reliability" in result.content
        assert "efficiency" in result.content
        assert "health" in result.content
    
    def test_monitor_invalid_action(self):
        """Test de acción inválida."""
        tool = MonitorTool()
        args = MonitorIn(action="invalid_action")
        
        result = tool(args)
        
        assert result.ok == False
        assert "error" in result.content


@pytest.fixture(autouse=True)
def reset_metrics_before_test():
    """Fixture para resetear métricas antes de cada test."""
    reset_metrics()
    yield
    reset_metrics()


class TestIntegration:
    """Tests de integración del sistema de observabilidad."""
    
    def test_full_observability_flow(self):
        """Test del flujo completo de observabilidad."""
        # 1. Ejecutar operaciones con spans
        with span("test_operation_1") as span_ctx:
            pass
        
        with span("test_operation_2") as span_ctx:
            pass
        
        # 2. Obtener métricas
        summary = get_metrics_summary()
        assert len(summary["operations"]) == 2
        
        # 3. Actualizar dashboard
        dashboard_update = update_dashboard()
        assert "dashboard" in dashboard_update
        assert "metrics" in dashboard_update
        
        # 4. Obtener KPIs
        kpis = get_kpis()
        assert "performance" in kpis
        assert "reliability" in kpis
        
        # 5. Usar herramienta de monitoreo
        monitor_tool = MonitorTool()
        result = monitor_tool(MonitorIn(action="kpis"))
        assert result.ok == True
