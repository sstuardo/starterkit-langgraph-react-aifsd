"""
Herramienta `monitor` para observabilidad y métricas del agente.

Propósito:
  Proporcionar acceso programático a métricas, KPIs y estado del sistema
  de observabilidad. Útil para monitoreo en tiempo real, debugging y
  análisis de rendimiento del agente ReAct.
"""

from src.core.metrics_dashboard import get_dashboard, get_kpis, update_dashboard
from src.core.observability import get_metrics_summary
from src.core.tool_interface import ToolInput, ToolOutput


class MonitorIn(ToolInput):
    """
    Entrada para la herramienta Monitor.

    Propósito:
      Estructurar los parámetros de monitoreo solicitados.

    Atributos:
      action: Acción a realizar (kpis, metrics, dashboard, alerts, trends).
      operation: Operación específica a monitorear (opcional).
      hours: Período en horas para tendencias (opcional).
      format: Formato de salida (json, summary).
    """

    action: str = "kpis"  # kpis, metrics, dashboard, alerts, trends
    operation: str = None  # Operación específica
    hours: int = 24  # Período para tendencias
    format: str = "summary"  # json, summary


class MonitorTool:
    """Tool de monitoreo para observabilidad del agente.

    Propósito:
      Proporcionar métricas, KPIs y estado del sistema de observabilidad
      en tiempo real.

    Atributos:
      name: Nombre canónico de la tool.
      description: Descripción corta del comportamiento de la tool.
      input_schema: Esquema Pydantic esperado como entrada (`MonitorIn`).
      output_schema: Esquema Pydantic producido como salida (`ToolOutput`).
      timeout_s: Tiempo máximo de ejecución sugerido en segundos.
    """

    name: str = "monitor"
    description: str = (
        "Monitorea métricas, KPIs y estado del sistema de observabilidad."
    )
    input_schema = MonitorIn
    output_schema = ToolOutput
    timeout_s: int = 5

    def __call__(self, args: MonitorIn) -> ToolOutput:
        """Ejecuta la herramienta Monitor.

        Propósito:
          Retornar métricas, KPIs o estado del sistema según la acción
          solicitada.

        Args:
          args: Parámetros tipados de entrada (`MonitorIn`), incluyendo
                la acción y parámetros opcionales.

        Returns:
          ToolOutput: Objeto con `ok=True` y `content` conteniendo las
                      métricas solicitadas.
        """
        try:
            if args.action == "kpis":
                content = self._get_kpis()
            elif args.action == "metrics":
                content = self._get_metrics(args.operation)
            elif args.action == "dashboard":
                content = self._get_dashboard()
            elif args.action == "alerts":
                content = self._get_alerts()
            elif args.action == "trends":
                content = self._get_trends(args.hours)
            else:
                return ToolOutput(
                    ok=False,
                    content={"error": f"Acción no válida: {args.action}"}
                )

            # Formatear salida según el formato solicitado
            if args.format == "json":
                return ToolOutput(ok=True, content=content)
            else:  # summary
                return ToolOutput(
                    ok=True,
                    content=self._format_summary(content, args.action)
                )

        except Exception as e:
            return ToolOutput(
                ok=False,
                content={"error": f"Error en monitoreo: {str(e)}"}
            )

    def _get_kpis(self) -> dict:
        """Obtiene KPIs clave del sistema."""
        return get_kpis()

    def _get_metrics(self, operation: str = None) -> dict:
        """Obtiene métricas detalladas."""
        if operation:
            return get_metrics_summary(operation)
        return get_metrics_summary()

    def _get_dashboard(self) -> dict:
        """Obtiene estado completo del dashboard."""
        return update_dashboard()

    def _get_alerts(self) -> dict:
        """Obtiene alertas activas del sistema."""
        dashboard = get_dashboard()
        active_alerts = [a for a in dashboard.alerts if not a["acknowledged"]]

        return {
            "active_alerts": len(active_alerts),
            "total_alerts": len(dashboard.alerts),
            "alerts": active_alerts[:10]  # Últimas 10 alertas activas
        }

    def _get_trends(self, hours: int) -> dict:
        """Obtiene tendencias de métricas."""
        dashboard = get_dashboard()
        return dashboard.get_metrics_trend(hours)

    def _format_summary(self, content: dict, action: str) -> dict:
        """Formatea el contenido en un resumen legible."""
        if action == "kpis":
            return self._format_kpis_summary(content)
        elif action == "metrics":
            return self._format_metrics_summary(content)
        elif action == "dashboard":
            return self._format_dashboard_summary(content)
        elif action == "alerts":
            return self._format_alerts_summary(content)
        elif action == "trends":
            return self._format_trends_summary(content)

        return content

    def _format_kpis_summary(self, kpis: dict) -> dict:
        """Formatea KPIs en un resumen legible."""
        return {
            "summary": "KPIs del Sistema",
            "performance": {
                "latencia_p50": f"{kpis['performance']['latency_p50_ms']:.1f}ms",
                "latencia_p95": f"{kpis['performance']['latency_p95_ms']:.1f}ms",
                "latencia_p99": f"{kpis['performance']['latency_p99_ms']:.1f}ms"
            },
            "reliability": {
                "tasa_exito": f"{kpis['reliability']['success_rate']*100:.1f}%",
                "tasa_error": f"{kpis['reliability']['error_rate']*100:.1f}%",
                "total_pasos": kpis['reliability']['total_steps']
            },
            "efficiency": {
                "total_tokens": kpis['efficiency']['total_tokens'],
                "costo_estimado": f"${kpis['efficiency']['estimated_cost_usd']:.4f}",
                "llamadas_tools": kpis['efficiency']['tool_calls']
            },
            "health": {
                "alertas_activas": kpis['health']['active_alerts'],
                "violaciones_slo": kpis['health']['slo_violations'],
                "ultima_actualizacion": kpis['health']['last_update']
            }
        }

    def _format_metrics_summary(self, metrics: dict) -> dict:
        """Formatea métricas en un resumen legible."""
        if "global_metrics" in metrics:
            global_metrics = metrics["global_metrics"]
            return {
                "summary": "Métricas Globales",
                "pasos": global_metrics.get("total_steps", 0),
                "tokens": global_metrics.get("total_tokens", 0),
                "costo": f"${global_metrics.get('estimated_cost_usd', 0.0):.4f}",
                "tasa_exito": (
                    f"{global_metrics.get('tool_success_rate', 0.0)*100:.1f}%"
                ),
                "operaciones": len(metrics.get("operations", {}))
            }
        else:
            return {
                "summary": "Métricas de Operación",
                "operacion": metrics.get("operation", "N/A"),
                "pasos": metrics.get("metrics", {}).get("total_steps", 0),
                "tokens": metrics.get("metrics", {}).get("total_tokens", 0),
                "costo": (
                    f"${metrics.get('metrics', {}).get('estimated_cost_usd', 0.0):.4f}"
                )
            }

    def _format_dashboard_summary(self, dashboard: dict) -> dict:
        """Formatea dashboard en un resumen legible."""
        return {
            "summary": "Estado del Dashboard",
            "ultima_actualizacion": dashboard["dashboard"]["last_update"],
            "total_slos": dashboard["dashboard"]["total_slos"],
            "alertas_activas": dashboard["dashboard"]["active_alerts"],
            "violaciones": dashboard["dashboard"]["total_violations"],
            "metricas_disponibles": len(dashboard["metrics"].get("operations", {}))
        }

    def _format_alerts_summary(self, alerts: dict) -> dict:
        """Formatea alertas en un resumen legible."""
        return {
            "summary": "Estado de Alertas",
            "alertas_activas": alerts["active_alerts"],
            "total_alertas": alerts["total_alerts"],
            "ultimas_alertas": [
                {
                    "severidad": alert["severity"],
                    "mensaje": alert["message"],
                    "timestamp": alert["timestamp"]
                }
                for alert in alerts["alerts"][:5]  # Solo las primeras 5
            ]
        }

    def _format_trends_summary(self, trends: dict) -> dict:
        """Formatea tendencias en un resumen legible."""
        if "message" in trends:
            return {"summary": "Tendencias", "mensaje": trends["message"]}

        return {
            "summary": "Análisis de Tendencias",
            "periodo_horas": trends["period_hours"],
            "puntos_datos": trends["data_points"],
            "metricas_analizadas": len(trends["trends"]),
            "tendencias": {
                metric: {
                    "tendencia": data["trend"],
                    "min": data["min"],
                    "max": data["max"],
                    "promedio": f"{data['avg']:.2f}"
                }
                for metric, data in trends["trends"].items()
            }
        }
