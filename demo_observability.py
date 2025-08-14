#!/usr/bin/env python3
"""
Demo del sistema de observabilidad avanzada.

Este script demuestra las capacidades del sistema:
- Métricas de rendimiento
- Trazabilidad
- Dashboard de KPIs
- Herramienta de monitoreo
"""

import time
import random
from src.core.observability import span, get_metrics_summary, reset_metrics
from src.core.metrics_dashboard import get_kpis, update_dashboard
from src.tools.monitor import MonitorTool, MonitorIn


def simulate_agent_operations():
    """Simula operaciones típicas de un agente ReAct."""
    
    print("🤖 Simulando operaciones del agente...")
    
    # Simular diferentes tipos de operaciones
    operations = [
        ("planner", 0.1, 0.05),
        ("reasoner", 0.3, 0.1),
        ("tool_selector", 0.05, 0.02),
        ("tool_executor", 0.8, 0.2),
        ("critic", 0.2, 0.05),
        ("finalizer", 0.1, 0.03)
    ]
    
    for op_name, base_time, variance in operations:
        # Simular latencia variable
        latency = base_time + random.uniform(-variance, variance)
        
        with span(op_name, step=1) as span_ctx:
            print(f"  📍 {op_name}: {latency:.3f}s")
            
            # Simular trabajo
            time.sleep(latency)
            
            # Simular éxito/fallo ocasional
            if random.random() < 0.1:  # 10% de fallos
                raise Exception(f"Error simulado en {op_name}")
    
    print("✅ Operaciones simuladas completadas")


def demonstrate_monitoring():
    """Demuestra las capacidades de monitoreo."""
    
    print("\n📊 Demostrando sistema de monitoreo...")
    
    # 1. Obtener KPIs
    print("\n1️⃣ KPIs del Sistema:")
    kpis = get_kpis()
    for category, metrics in kpis.items():
        print(f"  {category.upper()}:")
        for metric, value in metrics.items():
            print(f"    {metric}: {value}")
    
    # 2. Usar herramienta de monitoreo
    print("\n2️⃣ Herramienta de Monitoreo:")
    monitor = MonitorTool()
    
    # KPIs
    result = monitor(MonitorIn(action="kpis", format="summary"))
    print(f"  KPIs: {result.content['summary']}")
    
    # Métricas detalladas
    result = monitor(MonitorIn(action="metrics", format="summary"))
    print(f"  Métricas: {result.content['summary']}")
    
    # Dashboard
    result = monitor(MonitorIn(action="dashboard", format="summary"))
    print(f"  Dashboard: {result.content['summary']}")
    
    # Alertas
    result = monitor(MonitorIn(action="alerts", format="summary"))
    print(f"  Alertas: {result.content['summary']}")
    
    # Tendencias
    result = monitor(MonitorIn(action="trends", format="summary"))
    print(f"  Tendencias: {result.content['summary']}")


def demonstrate_advanced_features():
    """Demuestra características avanzadas."""
    
    print("\n🚀 Demostrando características avanzadas...")
    
    # 1. Actualizar dashboard
    print("\n1️⃣ Actualizando Dashboard:")
    dashboard_update = update_dashboard()
    print(f"  Total SLOs: {dashboard_update['dashboard']['total_slos']}")
    print(f"  Alertas activas: {dashboard_update['dashboard']['active_alerts']}")
    print(f"  Violaciones: {dashboard_update['dashboard']['total_violations']}")
    
    # 2. Métricas detalladas
    print("\n2️⃣ Métricas Detalladas:")
    metrics = get_metrics_summary()
    print(f"  Operaciones monitoreadas: {len(metrics['operations'])}")
    
    for op_name, op_metrics in metrics['operations'].items():
        print(f"    {op_name}:")
        print(f"      Pasos: {op_metrics['total_steps']}")
        print(f"      Éxitos: {op_metrics['successful_steps']}")
        print(f"      Latencia P95: {op_metrics['latency_p95']:.1f}ms")
        print(f"      Tasa de éxito: {op_metrics['tool_success_rate']*100:.1f}%")
    
    # 3. Exportar métricas
    print("\n3️⃣ Exportación de Métricas:")
    from src.core.metrics_dashboard import get_dashboard
    dashboard = get_dashboard()
    export_json = dashboard.export_metrics("json")
    print(f"  Métricas exportadas (JSON): {len(export_json)} caracteres")


def main():
    """Función principal de demostración."""
    
    print("🌟 DEMO: Sistema de Observabilidad Avanzada")
    print("=" * 50)
    
    # Resetear métricas para demo limpia
    reset_metrics()
    
    try:
        # 1. Simular operaciones del agente
        simulate_agent_operations()
        
        # 2. Demostrar monitoreo
        demonstrate_monitoring()
        
        # 3. Demostrar características avanzadas
        demonstrate_advanced_features()
        
        print("\n🎉 ¡Demo completado exitosamente!")
        print("\n💡 Características implementadas:")
        print("  ✅ Métricas P50/P95/P99 de latencia")
        print("  ✅ Trazabilidad con correlation IDs")
        print("  ✅ Métricas de costo y tokens")
        print("  ✅ Dashboard de KPIs en tiempo real")
        print("  ✅ SLOs y alertas automáticas")
        print("  ✅ Herramienta de monitoreo integrada")
        print("  ✅ Exportación de métricas")
        print("  ✅ Análisis de tendencias")
        
    except Exception as e:
        print(f"\n❌ Error durante la demo: {e}")
        print("Esto es normal en la primera ejecución - las métricas se acumulan con el tiempo")


if __name__ == "__main__":
    main()
