#!/usr/bin/env python3
"""
Demo Visual del Sistema de Observabilidad.

Este script crea visualizaciones bonitas y legibles del sistema:
- Gráficos ASCII de métricas
- Tablas formateadas de KPIs
- Indicadores visuales de estado
- Dashboard en consola
"""

import time
import random
import json
from datetime import datetime
from src.core.observability import span, get_metrics_summary, reset_metrics
from src.core.metrics_dashboard import get_kpis, update_dashboard
from src.tools.monitor import MonitorTool, MonitorIn


def print_header():
    """Imprime un header bonito para la demo."""
    print("🌟" * 20)
    print("🚀 SISTEMA DE OBSERVABILIDAD AVANZADA")
    print("🎯 ReAct + LangGraph + Métricas en Tiempo Real")
    print("🌟" * 20)
    print()


def print_metric_bar(value, max_value, width=40, label=""):
    """Imprime una barra de métrica visual."""
    if max_value == 0:
        percentage = 0
    else:
        percentage = min(100, (value / max_value) * 100)
    
    filled_width = int((percentage / 100) * width)
    bar = "█" * filled_width + "░" * (width - filled_width)
    
    print(f"{label:15} [{bar}] {percentage:5.1f}% ({value:8.2f})")


def print_latency_chart(metrics):
    """Imprime un gráfico de latencia."""
    print("📊 GRÁFICO DE LATENCIA")
    print("=" * 50)
    
    if not metrics.get("operations"):
        print("   No hay datos de latencia disponibles")
        return
    
    for op_name, op_metrics in metrics["operations"].items():
        p50 = op_metrics.get("latency_p50", 0)
        p95 = op_metrics.get("latency_p95", 0)
        p99 = op_metrics.get("latency_p99", 0)
        
        print(f"\n🔹 {op_name.upper()}")
        print_metric_bar(p50, 1000, 30, "  P50")
        print_metric_bar(p95, 1000, 30, "  P95")
        print_metric_bar(p99, 1000, 30, "  P99")


def print_performance_table(metrics):
    """Imprime una tabla de rendimiento."""
    print("\n📈 TABLA DE RENDIMIENTO")
    print("=" * 80)
    print(f"{'Operación':<20} {'Pasos':<8} {'Éxitos':<8} {'Errores':<8} {'Tasa Éxito':<12} {'Latencia P95':<15}")
    print("-" * 80)
    
    if not metrics.get("operations"):
        print("   No hay datos de rendimiento disponibles")
        return
    
    for op_name, op_metrics in metrics["operations"].items():
        total_steps = op_metrics.get("total_steps", 0)
        successful = op_metrics.get("successful_steps", 0)
        errors = op_metrics.get("failed_steps", 0)
        success_rate = op_metrics.get("tool_success_rate", 0) * 100
        latency_p95 = op_metrics.get("latency_p95", 0)
        
        print(f"{op_name:<20} {total_steps:<8} {successful:<8} {errors:<8} {success_rate:<11.1f}% {latency_p95:<14.1f}ms")


def print_kpis_dashboard():
    """Imprime un dashboard visual de KPIs."""
    print("\n🎯 DASHBOARD DE KPIs")
    print("=" * 60)
    
    kpis = get_kpis()
    
    # Performance
    print("\n🚀 PERFORMANCE")
    print("-" * 30)
    latency_p50 = kpis["performance"]["latency_p50_ms"]
    latency_p95 = kpis["performance"]["latency_p95_ms"]
    latency_p99 = kpis["performance"]["latency_p99_ms"]
    
    print(f"  📍 Latencia P50:  {latency_p50:>8.1f}ms")
    print(f"  📍 Latencia P95:  {latency_p95:>8.1f}ms")
    print(f"  📍 Latencia P99:  {latency_p99:>8.1f}ms")
    
    # Reliability
    print("\n🛡️  RELIABILITY")
    print("-" * 30)
    success_rate = kpis["reliability"]["success_rate"] * 100
    error_rate = kpis["reliability"]["error_rate"] * 100
    total_steps = kpis["reliability"]["total_steps"]
    
    print(f"  ✅ Tasa de Éxito: {success_rate:>8.1f}%")
    print(f"  ❌ Tasa de Error:  {error_rate:>8.1f}%")
    print(f"  🔄 Total Pasos:    {total_steps:>8}")
    
    # Efficiency
    print("\n⚡ EFFICIENCY")
    print("-" * 30)
    total_tokens = kpis["efficiency"]["total_tokens"]
    estimated_cost = kpis["efficiency"]["estimated_cost_usd"]
    tool_calls = kpis["efficiency"]["tool_calls"]
    
    print(f"  🎯 Total Tokens:   {total_tokens:>8}")
    print(f"  💰 Costo Estimado: ${estimated_cost:>7.4f}")
    print(f"  🛠️  Llamadas Tools: {tool_calls:>8}")
    
    # Health
    print("\n🏥 HEALTH")
    print("-" * 30)
    active_alerts = kpis["health"]["active_alerts"]
    slo_violations = kpis["health"]["slo_violations"]
    last_update = kpis["health"]["last_update"]
    
    print(f"  🚨 Alertas Activas:    {active_alerts:>8}")
    print(f"  ⚠️  Violaciones SLO:    {slo_violations:>8}")
    print(f"  🕐 Última Actualización: {last_update}")


def print_slo_status():
    """Imprime el estado de los SLOs."""
    print("\n🎯 ESTADO DE SLOs (Service Level Objectives)")
    print("=" * 60)
    
    dashboard_update = update_dashboard()
    violations = dashboard_update.get("violations", [])
    
    if not violations:
        print("  🟢 Todos los SLOs están siendo cumplidos")
        return
    
    print(f"  🔴 {len(violations)} SLO(s) violado(s):")
    for violation in violations:
        severity_icon = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "critical": "🚨"
        }.get(violation["severity"], "❓")
        
        print(f"    {severity_icon} {violation['slo_name']}: {violation['description']}")
        print(f"       Valor actual: {violation['current_value']} (umbral: {violation['threshold']})")


def print_alerts_summary():
    """Imprime un resumen de alertas."""
    print("\n🚨 RESUMEN DE ALERTAS")
    print("=" * 50)
    
    monitor = MonitorTool()
    result = monitor(MonitorIn(action="alerts", format="summary"))
    
    if result.ok:
        alerts_data = result.content
        active_alerts = alerts_data.get("alertas_activas", 0)
        total_alerts = alerts_data.get("total_alertas", 0)
        
        print(f"  📊 Total de alertas: {total_alerts}")
        print(f"  🔴 Alertas activas: {active_alerts}")
        
        if active_alerts > 0:
            print("\n  📋 Últimas alertas:")
            for alert in alerts_data.get("ultimas_alertas", [])[:3]:
                severity_icon = {
                    "info": "ℹ️",
                    "warning": "⚠️",
                    "error": "❌",
                    "critical": "🚨"
                }.get(alert["severidad"], "❓")
                
                print(f"    {severity_icon} {alert['mensaje']}")
                print(f"       {alert['timestamp']}")
    else:
        print("  ❌ Error al obtener alertas")


def simulate_operations_with_visuals():
    """Simula operaciones con feedback visual."""
    print("\n🤖 SIMULANDO OPERACIONES DEL AGENTE")
    print("=" * 50)
    
    operations = [
        ("planner", "🧠 Planificación", 0.2),
        ("reasoner", "💭 Razonamiento", 0.4),
        ("tool_selector", "🔧 Selección Tools", 0.1),
        ("tool_executor", "⚙️  Ejecución Tools", 0.6),
        ("critic", "🔍 Crítica", 0.3),
        ("finalizer", "🏁 Finalización", 0.2)
    ]
    
    for op_name, description, base_time in operations:
        print(f"\n📍 {description}")
        print(f"   Operación: {op_name}")
        
        with span(op_name, step=1) as span_ctx:
            # Simular trabajo con progreso visual
            actual_time = base_time + random.uniform(-0.1, 0.1)
            steps = 10
            for i in range(steps):
                progress = (i + 1) / steps
                bar_width = 20
                filled = int(progress * bar_width)
                bar = "█" * filled + "░" * (bar_width - filled)
                print(f"   Progreso: [{bar}] {progress*100:5.1f}%", end="\r")
                time.sleep(actual_time / steps)
            
            print(f"   ✅ Completado en {actual_time:.3f}s")
            
            # Simular éxito/fallo ocasional
            if random.random() < 0.15:  # 15% de fallos
                print(f"   ❌ Error simulado en {op_name}")
                raise Exception(f"Error simulado en {op_name}")


def print_final_summary():
    """Imprime un resumen final con estadísticas."""
    print("\n🎉 RESUMEN FINAL DE LA DEMO")
    print("=" * 50)
    
    metrics = get_metrics_summary()
    operations_count = len(metrics.get("operations", {}))
    
    print(f"  📊 Operaciones monitoreadas: {operations_count}")
    
    if operations_count > 0:
        total_steps = sum(op.get("total_steps", 0) for op in metrics["operations"].values())
        total_errors = sum(op.get("error_count", 0) for op in metrics["operations"].values())
        success_rate = ((total_steps - total_errors) / total_steps * 100) if total_steps > 0 else 0
        
        print(f"  🔄 Total de pasos: {total_steps}")
        print(f"  ❌ Total de errores: {total_errors}")
        print(f"  ✅ Tasa de éxito general: {success_rate:.1f}%")
    
    print("\n💡 Características demostradas:")
    print("  ✅ Métricas P50/P95/P99 de latencia")
    print("  ✅ Trazabilidad con correlation IDs")
    print("  ✅ Dashboard de KPIs en tiempo real")
    print("  ✅ SLOs y alertas automáticas")
    print("  ✅ Herramienta de monitoreo integrada")
    print("  ✅ Visualizaciones ASCII y tablas")
    print("  ✅ Análisis de tendencias")


def main():
    """Función principal de la demo visual."""
    print_header()
    
    # Resetear métricas para demo limpia
    reset_metrics()
    
    try:
        # 1. Simular operaciones con feedback visual
        simulate_operations_with_visuals()
        
        # 2. Mostrar métricas en tiempo real
        print("\n" + "="*60)
        print("📊 ANÁLISIS DE MÉTRICAS EN TIEMPO REAL")
        print("="*60)
        
        # 3. Dashboard de KPIs
        print_kpis_dashboard()
        
        # 4. Estado de SLOs
        print_slo_status()
        
        # 5. Resumen de alertas
        print_alerts_summary()
        
        # 6. Gráficos de latencia
        metrics = get_metrics_summary()
        print_latency_chart(metrics)
        
        # 7. Tabla de rendimiento
        print_performance_table(metrics)
        
        # 8. Resumen final
        print_final_summary()
        
    except Exception as e:
        print(f"\n❌ Error durante la demo: {e}")
        print("Esto es normal - las métricas se acumulan con el tiempo")
        
        # Mostrar métricas disponibles incluso con errores
        print("\n📊 Métricas capturadas hasta el error:")
        metrics = get_metrics_summary()
        print(json.dumps(metrics, indent=2, default=str))


if __name__ == "__main__":
    main()
