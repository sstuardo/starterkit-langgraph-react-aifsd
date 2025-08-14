#!/usr/bin/env python3
"""
Demo del Sistema de Seguridad y Control de Acceso para Presupuestos.

Este script demuestra cómo solo los usuarios administradores pueden:
- Crear políticas de presupuesto
- Modificar políticas existentes
- Eliminar políticas de usuario
- Los usuarios normales solo pueden ver presupuestos
"""

import time
from src.core.budget_management import (
    get_budget_summary, reset_budgets,
    create_policy_from_natural_language,
    get_user_budget_summary,
    add_user_profile, get_user_profile, is_admin_user,
    can_user_modify_policy, modify_budget_policy, remove_budget_policy,
    UserRole
)


def print_header():
    """Header bonito para la demo."""
    print("🔐" * 20)
    print("🚀 SISTEMA DE SEGURIDAD Y CONTROL DE ACCESO")
    print("🎯 Solo Administradores Pueden Modificar Presupuestos")
    print("🔐" * 20)
    print()


def setup_user_profiles():
    """Configura diferentes perfiles de usuario para la demo."""
    
    print("👥 Configurando Perfiles de Usuario...")
    
    # Usuario normal (solo puede ver)
    user_normal = add_user_profile(
        user_id="user_123",
        username="Juan Pérez",
        role=UserRole.USER
    )
    print(f"  👤 Usuario Normal: {user_normal.username} ({user_normal.role.value})")
    print(f"    - Permisos: {[p.value for p in user_normal.permissions]}")
    print(f"    - Puede modificar presupuestos: {user_normal.can_modify_budgets()}")
    
    # Administrador (puede crear y modificar)
    user_admin = add_user_profile(
        user_id="admin_456",
        username="María Admin",
        role=UserRole.ADMIN
    )
    print(f"  👑 Administrador: {user_admin.username} ({user_admin.role.value})")
    print(f"    - Permisos: {[p.value for p in user_admin.permissions]}")
    print(f"    - Puede modificar presupuestos: {user_admin.can_modify_budgets()}")
    
    # Super Administrador (control total)
    user_super = add_user_profile(
        user_id="super_789",
        username="Carlos Super",
        role=UserRole.SUPER_ADMIN
    )
    print(f"  👑👑 Super Admin: {user_super.username} ({user_super.role.value})")
    print(f"    - Permisos: {[p.value for p in user_super.permissions]}")
    print(f"    - Puede modificar presupuestos: {user_super.can_modify_budgets()}")
    
    return user_normal, user_admin, user_super


def demonstrate_user_permissions():
    """Demuestra las diferentes capacidades de cada tipo de usuario."""
    
    print("\n🔐 Demostrando Permisos de Usuario...")
    
    # 1. Verificar roles
    print("\n1️⃣ Verificación de Roles:")
    print(f"  👤 user_123 es admin: {is_admin_user('user_123')}")
    print(f"  👑 admin_456 es admin: {is_admin_user('admin_456')}")
    print(f"  👑👑 super_789 es admin: {is_admin_user('super_789')}")
    
    # 2. Verificar permisos para políticas específicas
    print("\n2️⃣ Permisos para Políticas:")
    
    # Política del sistema
    print(f"  📋 Política 'default_episode':")
    print(f"    - user_123 puede modificar: {can_user_modify_policy('user_123', 'default_episode')}")
    print(f"    - admin_456 puede modificar: {can_user_modify_policy('admin_456', 'default_episode')}")
    print(f"    - super_789 puede modificar: {can_user_modify_policy('super_789', 'default_episode')}")
    
    # Política de usuario (que crearemos)
    print(f"  📋 Política 'user_demo' (por crear):")
    print(f"    - user_123 puede modificar: {can_user_modify_policy('user_123', 'user_demo')}")
    print(f"    - admin_456 puede modificar: {can_user_modify_policy('admin_456', 'user_demo')}")
    print(f"    - super_789 puede modificar: {can_user_modify_policy('super_789', 'user_demo')}")


def demonstrate_policy_creation_permissions():
    """Demuestra quién puede crear políticas de presupuesto."""
    
    print("\n🚀 Demostrando Permisos de Creación de Políticas...")
    
    test_budget = "Quiero gastar máximo $10 por día"
    
    # 1. Usuario normal intenta crear política
    print("\n1️⃣ Usuario Normal Intenta Crear Política:")
    print(f"  👤 user_123: '{test_budget}'")
    
    result_user = create_policy_from_natural_language(
        budget_text=test_budget,
        user_id="user_123"
    )
    
    if result_user.get("success"):
        print(f"    ✅ Éxito: {result_user['message']}")
    else:
        print(f"    ❌ Error: {result_user['error']}")
    
    # 2. Administrador crea política
    print("\n2️⃣ Administrador Crea Política:")
    print(f"  👑 admin_456: '{test_budget}'")
    
    result_admin = create_policy_from_natural_language(
        budget_text=test_budget,
        user_id="admin_456"
    )
    
    if result_admin.get("success"):
        print(f"    ✅ Éxito: {result_admin['message']}")
        print(f"    📋 Política: {result_admin['policy_name']}")
    else:
        print(f"    ❌ Error: {result_admin['error']}")
    
    # 3. Super Admin crea política
    print("\n3️⃣ Super Admin Crea Política:")
    print(f"  👑👑 super_789: 'Límite de $50 por semana'")
    
    result_super = create_policy_from_natural_language(
        budget_text="Límite de $50 por semana",
        user_id="super_789"
    )
    
    if result_super.get("success"):
        print(f"    ✅ Éxito: {result_super['message']}")
        print(f"    📋 Política: {result_super['policy_name']}")
    else:
        print(f"    ❌ Error: {result_super['error']}")


def demonstrate_policy_modification_permissions():
    """Demuestra quién puede modificar políticas existentes."""
    
    print("\n🔧 Demostrando Permisos de Modificación...")
    
    # 1. Usuario normal intenta modificar
    print("\n1️⃣ Usuario Normal Intenta Modificar:")
    print(f"  👤 user_123 intenta modificar 'user_demo'")
    
    try:
        result = modify_budget_policy(
            policy_name="user_demo",
            user_id="user_123",
            limit_usd=15.0
        )
        print(f"    ✅ Éxito: Límite modificado a ${result.limit_usd}")
    except Exception as e:
        print(f"    ❌ Error: {str(e)}")
    
    # 2. Administrador modifica política
    print("\n2️⃣ Administrador Modifica Política:")
    print(f"  👑 admin_456 modifica 'user_demo'")
    
    try:
        result = modify_budget_policy(
            policy_name="user_demo",
            user_id="admin_456",
            limit_usd=12.0,
            description="Política modificada por administrador"
        )
        print(f"    ✅ Éxito: Límite modificado a ${result.limit_usd}")
        print(f"    📝 Descripción: {result.description}")
    except Exception as e:
        print(f"    ❌ Error: {str(e)}")
    
    # 3. Super Admin modifica política del sistema
    print("\n3️⃣ Super Admin Modifica Política del Sistema:")
    print(f"  👑👑 super_789 modifica 'default_episode'")
    
    try:
        result = modify_budget_policy(
            policy_name="default_episode",
            user_id="super_789",
            limit_usd=1.5
        )
        print(f"    ✅ Éxito: Límite modificado a ${result.limit_usd}")
    except Exception as e:
        print(f"    ❌ Error: {str(e)}")


def demonstrate_policy_deletion_permissions():
    """Demuestra quién puede eliminar políticas."""
    
    print("\n🗑️ Demostrando Permisos de Eliminación...")
    
    # 1. Usuario normal intenta eliminar
    print("\n1️⃣ Usuario Normal Intenta Eliminar:")
    print(f"  👤 user_123 intenta eliminar 'user_demo'")
    
    try:
        remove_budget_policy("user_demo", "user_123")
        print(f"    ✅ Éxito: Política eliminada")
    except Exception as e:
        print(f"    ❌ Error: {str(e)}")
    
    # 2. Administrador elimina política de usuario
    print("\n2️⃣ Administrador Elimina Política de Usuario:")
    print(f"  👑 admin_456 elimina 'user_demo'")
    
    try:
        remove_budget_policy("user_demo", "admin_456")
        print(f"    ✅ Éxito: Política eliminada")
    except Exception as e:
        print(f"    ❌ Error: {str(e)}")
    
    # 3. Super Admin intenta eliminar política del sistema
    print("\n3️⃣ Super Admin Intenta Eliminar Política del Sistema:")
    print(f"  👑👑 super_789 intenta eliminar 'default_episode'")
    
    try:
        remove_budget_policy("default_episode", "super_789")
        print(f"    ✅ Éxito: Política eliminada")
    except Exception as e:
        print(f"    ❌ Error: {str(e)}")


def demonstrate_security_features():
    """Demuestra características de seguridad del sistema."""
    
    print("\n🛡️ Demostrando Características de Seguridad...")
    
    # 1. Auditoría de cambios
    print("\n1️⃣ Auditoría de Cambios:")
    summary = get_budget_summary()
    
    for name, policy in summary["policies"].items():
        if hasattr(policy, 'created_by') and policy.created_by:
            print(f"  📋 {name}:")
            print(f"    - Creado por: {policy.created_by}")
            if hasattr(policy, 'modified_by') and policy.modified_by:
                print(f"    - Modificado por: {policy.modified_by}")
            if hasattr(policy, 'is_system_policy') and policy.is_system_policy:
                print(f"    - Tipo: Política del sistema (protegida)")
    
    # 2. Verificación de integridad
    print("\n2️⃣ Verificación de Integridad:")
    
    # Verificar que las políticas del sistema no se pueden eliminar
    system_policies = ["default_episode", "hourly_limit", "daily_limit", "per_operation"]
    
    for policy_name in system_policies:
        policy = get_budget_summary()["policies"].get(policy_name)
        if policy:
            is_system = getattr(policy, 'is_system_policy', False)
            print(f"  🔒 {policy_name}: {'Sistema' if is_system else 'Usuario'}")
    
    # 3. Resumen de seguridad
    print("\n3️⃣ Resumen de Seguridad:")
    print(f"  👥 Total usuarios: {len([u for u in ['user_123', 'admin_456', 'super_789'] if get_user_profile(u)])}")
    print(f"  👑 Usuarios admin: {len([u for u in ['user_123', 'admin_456', 'super_789'] if is_admin_user(u)])}")
    print(f"  📋 Total políticas: {len(summary['policies'])}")
    print(f"  🔒 Políticas del sistema: {len([p for p in summary['policies'].values() if getattr(p, 'is_system_policy', False)])}")


def main():
    """Función principal de demostración."""
    
    print("🔐 DEMO: Sistema de Seguridad y Control de Acceso")
    print("=" * 60)
    
    # Resetear presupuestos para demo limpia
    reset_budgets()
    
    try:
        # 1. Configurar perfiles de usuario
        user_normal, user_admin, user_super = setup_user_profiles()
        
        # 2. Demostrar permisos básicos
        demonstrate_user_permissions()
        
        # 3. Demostrar creación de políticas
        demonstrate_policy_creation_permissions()
        
        # 4. Demostrar modificación de políticas
        demonstrate_policy_modification_permissions()
        
        # 5. Demostrar eliminación de políticas
        demonstrate_policy_deletion_permissions()
        
        # 6. Demostrar características de seguridad
        demonstrate_security_features()
        
        print("\n🎉 ¡Demo de Seguridad completado exitosamente!")
        print("\n💡 Características de Seguridad implementadas:")
        print("  ✅ Sistema de roles (USER, ADMIN, SUPER_ADMIN)")
        print("  ✅ Control de acceso basado en permisos")
        print("  ✅ Solo administradores pueden modificar presupuestos")
        print("  ✅ Políticas del sistema están protegidas")
        print("  ✅ Auditoría completa de cambios")
        print("  ✅ Verificación de permisos en tiempo real")
        print("  ✅ Prevención de acceso no autorizado")
        
    except Exception as e:
        print(f"\n❌ Error durante la demo: {e}")


if __name__ == "__main__":
    main()
