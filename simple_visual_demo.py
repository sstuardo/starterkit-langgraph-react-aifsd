#!/usr/bin/env python3
"""
Demo Visual Simple del Sistema de Observabilidad.
"""

import time
import random
from src.core.observability import span, get_metrics_summary, reset_metrics
from src.core.metrics_dashboard import get_kpis, update_dashboard


def print_header():
    """Header bonito para la demo."""
    print("🌟" * 20)
    print("🚀 SISTEMA DE OBSERVABILIDAD AVANZADA")
    print("🎯 ReAct + LangGraph + Métricas en Tiempo Real")
    print("🌟" * 20)
    print()


def print_metric_bar(value, max_value, width=30, label=""):
    """Barra visual de métrica."""
    if max_value == 0:
        percentage = 0
    else:
        percentage = min(100, (value / max_value) * 100)
    
    filled_width = int((percentage / 100) * width)
    bar = "█" * filled_width + "░" * (width - filled_width)
    
    print(f"{label:15} [{bar}] {percentage:5.1f}%")


def simulate_operations():
    """Simula operaciones del agente."""
    print("🤖 Simulando operaciones del agente...")
    
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
        
        with span(op_name, step=1) as span_ctx:
            actual_time = base_time + random.uniform(-0.1, 0.1)
            time.sleep(actual_time)
            print(f"   ✅ Completado en {actual_time:.3f}s")


def show_metrics():
    """Muestra métricas en formato visual."""
    print("\n📊 MÉTRICAS EN TIEMPO REAL")
    print("=" * 50)
    
    metrics = get_metrics_summary()
    operations = metrics.get("operations", {})
    
    if not operations:
        print("   No hay métricas disponibles")
        return
    
    print(f"{'Operación':<20} {'Pasos':<8} {'Éxitos':<8} {'Latencia P95':<15}")
    print("-" * 60)
    
    for op_name, op_metrics in operations.items():
        total_steps = op_metrics.get("total_steps", 0)
        successful = op_metrics.get("successful_steps", 0)
        latency_p95 = op_metrics.get("latency_p95", 0)
        
        print(f"{op_name:<20} {total_steps:<8} {successful:<8} {latency_p95:<14.1f}ms")


def show_kpis():
    """Muestra KPIs principales."""
    print("\n🎯 KPIs PRINCIPALES")
    print("=" * 40)
    
    kpis = get_kpis()
    
    # Performance
    print("\n🚀 PERFORMANCE")
    latency_p95 = kpis["performance"]["latency_p95_ms"]
    print(f"  📍 Latencia P95: {latency_p95:>8.1f}ms")
    
    # Reliability
    print("\n🛡️  RELIABILITY")
    success_rate = kpis["reliability"]["success_rate"] * 100
    total_steps = kpis["reliability"]["total_steps"]
    print(f"  ✅ Tasa de Éxito: {success_rate:>8.1f}%")
    print(f"  🔄 Total Pasos:    {total_steps:>8}")
    
    # Efficiency
    print("\n⚡ EFFICIENCY")
    total_tokens = kpis["efficiency"]["total_tokens"]
    tool_calls = kpis["efficiency"]["tool_calls"]
    print(f"  🎯 Total Tokens:   {total_tokens:>8}")
    print(f"  🛠️  Llamadas Tools: {tool_calls:>8}")


def main():
    """Función principal."""
    print_header()
    
    # Resetear métricas
    reset_metrics()
    
    try:
        # Simular operaciones
        simulate_operations()
        
        # Mostrar métricas
        show_metrics()
        
        # Mostrar KPIs
        show_kpis()
        
        print("\n🎉 ¡Demo visual completado!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Mostrando métricas disponibles:")
        metrics = get_metrics_summary()
        print(f"Operaciones: {len(metrics.get('operations', {}))}")


if __name__ == "__main__":
    main()
