"""Dashboard de métricas para monitoreo de agentes ReAct + LangGraph.

Características:
- Visualización de KPIs en tiempo real
- Alertas automáticas basadas en SLOs
- Exportación de métricas
- Comparación de rendimiento
"""

import json
import time
from datetime import datetime, timedelta
from typing import Any

from .observability import get_metrics_summary


class SLODefinition:
    """Definición de Service Level Objectives."""

    def __init__(
        self,
        name: str,
        metric: str,
        threshold: float,
        operator: str = ">=",  # >=, <=, ==, !=
        severity: str = "warning",  # info, warning, error, critical
        description: str = "",
    ):
        self.name = name
        self.metric = metric
        self.threshold = threshold
        self.operator = operator
        self.severity = severity
        self.description = description

    def evaluate(self, value: float) -> bool:
        """Evalúa si el valor cumple con el SLO."""
        if self.operator == ">=":
            return value >= self.threshold
        elif self.operator == "<=":
            return value <= self.threshold
        elif self.operator == "==":
            return value == self.threshold
        elif self.operator == "!=":
            return value != self.threshold
        return False


class MetricsDashboard:
    """Dashboard principal para visualización y alertas de métricas."""

    def __init__(self):
        self.slos: list[SLODefinition] = []
        self.alerts: list[dict[str, Any]] = []
        self.metrics_history: list[dict[str, Any]] = []
        self.last_update = datetime.now()

        # SLOs por defecto
        self._setup_default_slos()

    def _setup_default_slos(self):
        """Configura SLOs por defecto para agentes ReAct."""

        # Latencia
        self.add_slo(
            "latency_p95_under_5s",
            "latency_p95",
            5000.0,  # 5 segundos
            "<=",
            "warning",
            "P95 de latencia debe estar bajo 5 segundos",
        )

        # Tasa de éxito
        self.add_slo(
            "success_rate_above_95",
            "tool_success_rate",
            0.95,  # 95%
            ">=",
            "error",
            "Tasa de éxito debe estar por encima del 95%",
        )

        # Tasa de error
        self.add_slo(
            "error_rate_below_5",
            "error_rate",
            0.05,  # 5%
            "<=",
            "warning",
            "Tasa de error debe estar por debajo del 5%",
        )

        # Presupuesto de tokens
        self.add_slo(
            "tokens_under_1000",
            "total_tokens",
            1000,
            "<=",
            "info",
            "Uso de tokens debe estar bajo 1000 por episodio",
        )

    def add_slo(
        self,
        name: str,
        metric: str,
        threshold: float,
        operator: str = ">=",
        severity: str = "warning",
        description: str = "",
    ):
        """Agrega un nuevo SLO."""
        slo = SLODefinition(name, metric, threshold, operator, severity, description)
        self.slos.append(slo)

    def evaluate_slos(self, metrics: dict[str, Any]) -> list[dict[str, Any]]:
        """Evalúa todos los SLOs contra las métricas actuales."""
        violations = []

        for slo in self.slos:
            # Buscar el valor de la métrica en las métricas globales
            global_metrics = metrics.get("global_metrics", {})
            operation_metrics = metrics.get("operations", {})

            # Buscar en métricas globales primero
            if slo.metric in global_metrics:
                value = global_metrics[slo.metric]
                if not slo.evaluate(value):
                    violations.append(
                        {
                            "slo_name": slo.name,
                            "metric": slo.metric,
                            "current_value": value,
                            "threshold": slo.threshold,
                            "operator": slo.operator,
                            "severity": slo.severity,
                            "description": slo.description,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )

            # Buscar en métricas de operaciones específicas
            else:
                for op_name, op_metrics in operation_metrics.items():
                    if slo.metric in op_metrics:
                        value = op_metrics[slo.metric]
                        if not slo.evaluate(value):
                            violations.append(
                                {
                                    "slo_name": slo.name,
                                    "operation": op_name,
                                    "metric": slo.metric,
                                    "current_value": value,
                                    "threshold": slo.threshold,
                                    "operator": slo.operator,
                                    "severity": slo.severity,
                                    "description": slo.description,
                                    "timestamp": datetime.now().isoformat(),
                                }
                            )

        return violations

    def update(self) -> dict[str, Any]:
        """Actualiza el dashboard con métricas frescas."""
        metrics = get_metrics_summary()
        violations = self.evaluate_slos(metrics)

        # Agregar alertas si hay violaciones
        for violation in violations:
            alert = {
                "id": f"alert_{int(time.time())}_{violation['slo_name']}",
                "type": "slo_violation",
                "severity": violation["severity"],
                "message": (
                    f"SLO '{violation['slo_name']}' violado: {violation['description']}"
                ),
                "details": violation,
                "timestamp": datetime.now().isoformat(),
                "acknowledged": False,
            }
            self.alerts.append(alert)

        # Actualizar historial
        self.metrics_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "metrics": metrics,
                "violations": violations,
            }
        )

        # Mantener solo las últimas 100 entradas
        if len(self.metrics_history) > 100:
            self.metrics_history = self.metrics_history[-100:]

        self.last_update = datetime.now()

        return {
            "dashboard": {
                "last_update": self.last_update.isoformat(),
                "total_slos": len(self.slos),
                "active_alerts": len([a for a in self.alerts if not a["acknowledged"]]),
                "total_violations": len(violations),
            },
            "metrics": metrics,
            "violations": violations,
            "recent_alerts": self.alerts[-10:],  # Últimas 10 alertas
        }

    def get_kpis(self) -> dict[str, Any]:
        """Obtiene KPIs clave para monitoreo."""
        metrics = get_metrics_summary()
        global_metrics = metrics.get("global_metrics", {})

        return {
            "performance": {
                "latency_p50_ms": global_metrics.get("latency_p50", 0.0),
                "latency_p95_ms": global_metrics.get("latency_p95", 0.0),
                "latency_p99_ms": global_metrics.get("latency_p99", 0.0),
            },
            "reliability": {
                "success_rate": global_metrics.get("tool_success_rate", 0.0),
                "error_rate": global_metrics.get("error_rate", 0.0),
                "total_steps": global_metrics.get("total_steps", 0),
            },
            "efficiency": {
                "total_tokens": global_metrics.get("total_tokens", 0),
                "estimated_cost_usd": global_metrics.get("estimated_cost_usd", 0.0),
                "tool_calls": global_metrics.get("tool_calls", 0),
            },
            "health": {
                "active_alerts": len([a for a in self.alerts if not a["acknowledged"]]),
                "slo_violations": len(self.evaluate_slos(metrics)),
                "last_update": self.last_update.isoformat(),
            },
        }

    def acknowledge_alert(self, alert_id: str):
        """Marca una alerta como reconocida."""
        for alert in self.alerts:
            if alert["id"] == alert_id:
                alert["acknowledged"] = True
                break

    def export_metrics(self, format: str = "json") -> str:
        """Exporta métricas en diferentes formatos."""
        metrics = get_metrics_summary()

        if format == "json":
            return json.dumps(metrics, indent=2, default=str)
        elif format == "csv":
            # Implementar exportación CSV si es necesario
            return "CSV export not implemented yet"
        else:
            return f"Unsupported format: {format}"

    def get_metrics_trend(self, hours: int = 24) -> dict[str, Any]:
        """Obtiene tendencias de métricas en las últimas N horas."""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        relevant_history = [
            entry
            for entry in self.metrics_history
            if datetime.fromisoformat(entry["timestamp"]) > cutoff_time
        ]

        if not relevant_history:
            return {"message": "No hay datos suficientes para el período solicitado"}

        # Calcular tendencias básicas
        trends = {}
        for entry in relevant_history:
            metrics = entry["metrics"]
            global_metrics = metrics.get("global_metrics", {})

            for metric_name, value in global_metrics.items():
                if metric_name not in trends:
                    trends[metric_name] = []
                trends[metric_name].append(value)

        # Calcular estadísticas de tendencia
        trend_analysis = {}
        for metric_name, values in trends.items():
            if len(values) > 1:
                trend_analysis[metric_name] = {
                    "values": values,
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "trend": (
                        "increasing"
                        if values[-1] > values[0]
                        else "decreasing"
                        if values[-1] < values[0]
                        else "stable"
                    ),
                }

        return {
            "period_hours": hours,
            "data_points": len(relevant_history),
            "trends": trend_analysis,
        }


# Instancia global del dashboard
dashboard = MetricsDashboard()


def get_dashboard() -> MetricsDashboard:
    """Obtiene la instancia global del dashboard."""
    return dashboard


def update_dashboard() -> dict[str, Any]:
    """Actualiza y obtiene el estado del dashboard."""
    return dashboard.update()


def get_kpis() -> dict[str, Any]:
    """Obtiene KPIs clave del dashboard."""
    return dashboard.get_kpis()
