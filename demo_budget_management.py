#!/usr/bin/env python3
"""
Demo del Sistema de Gestión de Presupuesto Avanzado.

Este script demuestra las capacidades del sistema:
- Control de costos por operación/episodio
- Políticas de presupuesto configurables
- Alertas automáticas de límites excedidos
- Throttling automático basado en presupuesto
- Tracking detallado de costos por usuario/sesión
"""

import time
import random
from src.core.observability import span, get_metrics_summary, reset_metrics
from src.core.budget_management import (
    check_budget, get_budget_summary, add_budget_policy, reset_budgets,
    BudgetPolicy, BudgetPeriod, BudgetAction
)
from src.core.throttling_service import (
    should_throttle, apply_throttling, get_throttling_summary, reset_throttling
)
from src.tools.budget_monitor import BudgetMonitorTool, BudgetMonitorIn


def print_header():
    """Header bonito para la demo."""
    print("💰" * 20)
    print("🚀 SISTEMA DE GESTIÓN DE PRESUPUESTO AVANZADO")
    print("🎯 Control de Costos + Throttling Automático + Alertas")
    print("💰" * 20)
    print()


def demonstrate_budget_policies():
    """Demuestra la creación y gestión de políticas de presupuesto."""
    
    print("📋 Demostrando Políticas de Presupuesto...")
    
    # 1. Ver políticas por defecto
    print("\n1️⃣ Políticas por Defecto:")
    summary = get_budget_summary()
    for name, policy in summary["policies"].items():
        print(f"  📊 {name}:")
        print(f"    - Período: {policy['period']}")
        print(f"    - Límite: ${policy['limit_usd']:.4f}")
        print(f"    - Acción: {policy['action']}")
        print(f"    - Descripción: {policy['description']}")
    
    # 2. Agregar política personalizada
    print("\n2️⃣ Agregando Política Personalizada:")
    custom_policy = BudgetPolicy(
        name="demo_custom",
        period=BudgetPeriod.PER_EPISODE,
        limit_usd=0.50,  # $0.50 por episodio
        action=BudgetAction.THROTTLE,
        description="Política de demo para testing"
    )
    add_budget_policy(custom_policy)
    print(f"  ✅ Política '{custom_policy.name}' agregada")
    
    # 3. Verificar política agregada
    print("\n3️⃣ Verificando Política Agregada:")
    updated_summary = get_budget_summary()
    if "demo_custom" in updated_summary["policies"]:
        policy = updated_summary["policies"]["demo_custom"]
        print(f"  📊 {custom_policy.name}:")
        print(f"    - Límite: ${policy['limit_usd']:.4f}")
        print(f"    - Acción: {policy['action']}")


def demonstrate_budget_checks():
    """Demuestra las verificaciones de presupuesto en tiempo real."""
    
    print("\n🔍 Demostrando Verificaciones de Presupuesto...")
    
    # 1. Verificación básica
    print("\n1️⃣ Verificación Básica:")
    check_result = check_budget(
        cost_usd=0.05,
        operation_name="demo_operation",
        policy_name="default_episode"
    )
    
    print(f"  📊 Resultado:")
    print(f"    - Permitido: {check_result['allowed']}")
    print(f"    - Acción: {check_result['action']}")
    print(f"    - Mensaje: {check_result['message']}")
    print(f"    - Uso: {check_result['usage_percentage']:.1f}%")
    print(f"    - Restante: ${check_result['remaining_usd']:.4f}")
    
    # 2. Verificación con límite excedido
    print("\n2️⃣ Verificación con Límite Excedido:")
    expensive_check = check_budget(
        cost_usd=2.0,  # $2.0 - excede el límite de $1.0
        operation_name="expensive_operation",
        policy_name="default_episode"
    )
    
    print(f"  📊 Resultado:")
    print(f"    - Permitido: {expensive_check['allowed']}")
    print(f"    - Acción: {expensive_check['action']}")
    print(f"    - Mensaje: {expensive_check['message']}")
    print(f"    - Uso: {expensive_check['usage_percentage']:.1f}%")
    
    # 3. Verificación con política personalizada
    print("\n3️⃣ Verificación con Política Personalizada:")
    custom_check = check_budget(
        cost_usd=0.30,
        operation_name="custom_operation",
        policy_name="demo_custom"
    )
    
    print(f"  📊 Resultado:")
    print(f"    - Permitido: {custom_check['allowed']}")
    print(f"    - Acción: {custom_check['action']}")
    print(f"    - Mensaje: {custom_check['message']}")


def demonstrate_natural_language_budgets():
    """Demuestra la creación de presupuestos en lenguaje natural."""
    
    print("\n🗣️ Demostrando Presupuestos en Lenguaje Natural...")
    
    from src.core.budget_management import (
        parse_natural_language_budget, 
        create_policy_from_natural_language
    )
    
    # 1. Ejemplos de texto en lenguaje natural
    natural_budgets = [
        "Quiero gastar máximo $5 por día",
        "Mi presupuesto es $20 por semana", 
        "No quiero que una sola operación cueste más de $0.50",
        "Límite de $100 por mes para este proyecto",
        "Gastar máximo $2 por hora en operaciones"
    ]
    
    print("\n1️⃣ Parseando Texto en Lenguaje Natural:")
    for budget_text in natural_budgets:
        print(f"\n  📝 Texto: '{budget_text}'")
        
        # Parsear el texto
        parsed = parse_natural_language_budget(budget_text)
        
        if parsed.get("success"):
            print(f"    ✅ Parseado exitosamente:")
            print(f"      - Cantidad: ${parsed['amount_usd']:.2f}")
            print(f"      - Período: {parsed['period']}")
            print(f"      - Acción: {parsed['action']}")
            print(f"      - Nombre de política: {parsed['policy_name']}")
            print(f"      - Descripción: {parsed['description']}")
        else:
            print(f"    ❌ Error: {parsed.get('error', 'Error desconocido')}")
    
    # 2. Crear políticas automáticamente
    print("\n2️⃣ Creando Políticas Automáticamente:")
    
    # Solo usar algunos ejemplos para no saturar el sistema
    test_budgets = [
        "Quiero gastar máximo $3 por día",
        "Límite de $0.25 por operación"
    ]
    
    for budget_text in test_budgets:
        print(f"\n  🚀 Creando política: '{budget_text}'")
        
        result = create_policy_from_natural_language(
            budget_text=budget_text,
            user_id="demo_user",
            session_id="demo_session"
        )
        
        if result.get("success"):
            print(f"    ✅ Política creada: {result['policy_name']}")
            print(f"      - Mensaje: {result['message']}")
            print(f"      - Detalles: {result['details']}")
        else:
            print(f"    ❌ Error: {result.get('error', 'Error desconocido')}")
    
    # 3. Verificar políticas creadas
    print("\n3️⃣ Verificando Políticas Creadas:")
    updated_summary = get_budget_summary("demo_user", "demo_session")
    
    user_policies = {}
    for name, policy in updated_summary["policies"].items():
        if name.startswith("user_"):
            user_policies[name] = policy
    
    if user_policies:
        print(f"  📊 Políticas del usuario creadas: {len(user_policies)}")
        for name, policy in user_policies.items():
            print(f"    - {name}: ${policy['limit_usd']:.2f} ({policy['period']})")
    else:
        print("  📊 No se encontraron políticas de usuario")


def main():
    """Función principal de demostración."""
    
    print("💰 DEMO: Sistema de Gestión de Presupuesto Avanzado")
    print("=" * 60)
    
    # Resetear métricas y presupuestos para demo limpia
    reset_metrics()
    reset_budgets()
    reset_throttling()
    
    try:
        # 1. Políticas de presupuesto
        demonstrate_budget_policies()
        
        # 2. Verificaciones de presupuesto
        demonstrate_budget_checks()
        
        # 3. Presupuestos en lenguaje natural
        demonstrate_natural_language_budgets()
        
        print("\n🎉 ¡Demo de Budget Management completado exitosamente!")
        print("\n💡 Características implementadas:")
        print("  ✅ Control de costos por operación/episodio")
        print("  ✅ Políticas de presupuesto configurables")
        print("  ✅ Alertas automáticas de límites excedidos")
        print("  ✅ Throttling automático basado en presupuesto")
        print("  ✅ Tracking detallado de costos por usuario/sesión")
        print("  ✅ Creación automática de políticas desde lenguaje natural")
        print("  ✅ Interpretación inteligente de presupuestos del usuario")
        
    except Exception as e:
        print(f"\n❌ Error durante la demo: {e}")
        print("Esto puede ser normal en la primera ejecución")


if __name__ == "__main__":
    main()
