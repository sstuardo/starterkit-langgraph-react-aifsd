#!/usr/bin/env python3
"""
Sistema de Gestión de Presupuesto Avanzado.

Este módulo implementa:
- Control de costos por operación/episodio
- Políticas de presupuesto configurables
- Alertas automáticas de límites excedidos
- Throttling automático basado en presupuesto
- Tracking detallado de costos por usuario/sesión
"""

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from collections import defaultdict

import structlog

# Configurar logging estructurado
log = structlog.get_logger()


class UserRole(Enum):
    """Roles de usuario disponibles."""
    USER = "user"           # Usuario regular - solo puede ver
    ADMIN = "admin"         # Administrador - puede modificar
    SUPER_ADMIN = "super_admin"  # Super admin - control total


class BudgetPermission(Enum):
    """Permisos disponibles para presupuestos."""
    VIEW = "view"           # Ver presupuestos
    CREATE = "create"       # Crear políticas
    MODIFY = "modify"       # Modificar políticas existentes
    DELETE = "delete"       # Eliminar políticas
    OVERRIDE = "override"   # Anular límites temporalmente


@dataclass
class UserProfile:
    """Perfil de usuario con roles y permisos."""
    
    user_id: str
    username: str
    role: UserRole = UserRole.USER
    permissions: List[BudgetPermission] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Configurar permisos por defecto según el rol."""
        if self.role == UserRole.USER:
            self.permissions = [BudgetPermission.VIEW]
        elif self.role == UserRole.ADMIN:
            self.permissions = [
                BudgetPermission.VIEW,
                BudgetPermission.CREATE,
                BudgetPermission.MODIFY
            ]
        elif self.role == UserRole.SUPER_ADMIN:
            self.permissions = [perm for perm in BudgetPermission]
    
    def has_permission(self, permission: BudgetPermission) -> bool:
        """Verifica si el usuario tiene un permiso específico."""
        return permission in self.permissions
    
    def can_modify_budgets(self) -> bool:
        """Verifica si el usuario puede modificar presupuestos."""
        return any(perm in [BudgetPermission.CREATE, BudgetPermission.MODIFY] 
                  for perm in self.permissions)


class BudgetPeriod(Enum):
    """Períodos de presupuesto disponibles."""
    PER_OPERATION = "per_operation"
    PER_EPISODE = "per_episode"
    PER_HOUR = "per_hour"
    PER_DAY = "per_day"
    PER_WEEK = "per_week"
    PER_MONTH = "per_month"


class BudgetAction(Enum):
    """Acciones cuando se excede el presupuesto."""
    WARN = "warn"           # Solo advertencia
    THROTTLE = "throttle"   # Reducir velocidad
    BLOCK = "block"         # Bloquear completamente
    GRACEFUL_DEGRADATION = "graceful_degradation"  # Degradar calidad


@dataclass
class BudgetPolicy:
    """Política de presupuesto configurable."""
    
    name: str
    period: BudgetPeriod
    limit_usd: float
    action: BudgetAction = BudgetAction.WARN
    description: str = ""
    
    # Configuraciones adicionales
    soft_limit_usd: Optional[float] = None  # Límite suave para advertencias
    grace_period_minutes: int = 5  # Período de gracia antes de bloquear
    
    # Métricas específicas
    max_tokens_per_operation: Optional[int] = None
    max_operations_per_period: Optional[int] = None
    
    # Notificaciones
    notify_on_soft_limit: bool = True
    notify_on_hard_limit: bool = True
    
    # Control de acceso
    created_by: Optional[str] = None  # ID del usuario que creó la política
    created_at: datetime = field(default_factory=datetime.now)
    modified_by: Optional[str] = None  # ID del último usuario que modificó
    modified_at: Optional[datetime] = None
    is_system_policy: bool = False  # Si es una política del sistema (no modificable)
    
    def __post_init__(self):
        """Validar configuración de la política."""
        if self.soft_limit_usd is None:
            self.soft_limit_usd = self.limit_usd * 0.8  # 80% del límite duro
        
        if self.limit_usd <= 0:
            raise ValueError("El límite de presupuesto debe ser positivo")
        
        if self.soft_limit_usd >= self.limit_usd:
            raise ValueError("El límite suave debe ser menor al límite duro")
    
    def can_be_modified_by(self, user_profile: UserProfile) -> bool:
        """Verifica si un usuario puede modificar esta política."""
        if not user_profile.can_modify_budgets():
            return False
        
        # Los usuarios normales no pueden modificar políticas del sistema
        if self.is_system_policy and user_profile.role == UserRole.USER:
            return False
        
        # Los super admins pueden modificar todo
        if user_profile.role == UserRole.SUPER_ADMIN:
            return True
        
        # Los admins pueden modificar políticas de usuario
        if user_profile.role == UserRole.ADMIN:
            return not self.is_system_policy or self.created_by == user_profile.user_id
        
        return False


@dataclass
class BudgetUsage:
    """Uso actual del presupuesto."""
    
    period_start: datetime
    current_usd: float = 0.0
    operations_count: int = 0
    total_tokens: int = 0
    
    # Historial de operaciones
    operations: List[Dict[str, Any]] = field(default_factory=list)
    
    # Alertas generadas
    alerts_generated: List[str] = field(default_factory=list)
    
    def add_operation(self, cost_usd: float, tokens: int, operation_name: str):
        """Agrega una operación al uso del presupuesto."""
        self.current_usd += cost_usd
        self.total_tokens += tokens
        self.operations_count += 1
        
        self.operations.append({
            "timestamp": datetime.now().isoformat(),
            "operation": operation_name,
            "cost_usd": cost_usd,
            "tokens": tokens
        })
    
    def get_usage_percentage(self, limit_usd: float) -> float:
        """Obtiene el porcentaje de uso del presupuesto."""
        if limit_usd == 0:
            return 0.0
        return (self.current_usd / limit_usd) * 100
    
    def is_soft_limit_exceeded(self, soft_limit_usd: float) -> bool:
        """Verifica si se excedió el límite suave."""
        return self.current_usd >= soft_limit_usd
    
    def is_hard_limit_exceeded(self, hard_limit_usd: float) -> bool:
        """Verifica si se excedió el límite duro."""
        return self.current_usd >= hard_limit_usd


class BudgetManager:
    """Gestor centralizado de presupuestos del sistema."""
    
    def __init__(self):
        """Inicializa el gestor de presupuestos."""
        self.policies: Dict[str, BudgetPolicy] = {}
        self.usage: Dict[str, BudgetUsage] = {}
        self.user_budgets: Dict[str, Dict[str, BudgetUsage]] = defaultdict(dict)
        self.session_budgets: Dict[str, Dict[str, BudgetUsage]] = defaultdict(dict)
        
        # Sistema de usuarios y roles
        self.user_profiles: Dict[str, UserProfile] = {}
        self.admin_users: set = set()
        
        # Configurar políticas por defecto
        self._setup_default_policies()
        
        # Callbacks para notificaciones
        self.budget_callbacks: List[callable] = []
        
        log.info("budget_manager.initialized", policies_count=len(self.policies))
    
    def _setup_default_policies(self):
        """Configura políticas de presupuesto por defecto."""
        
        # Política por episodio (default)
        self.add_policy(BudgetPolicy(
            name="default_episode",
            period=BudgetPeriod.PER_EPISODE,
            limit_usd=1.0,  # $1 por episodio
            action=BudgetAction.THROTTLE,
            description="Límite por defecto por episodio de agente",
            is_system_policy=True,
            created_by="system"
        ))
        
        # Política por hora
        self.add_policy(BudgetPolicy(
            name="hourly_limit",
            period=BudgetPeriod.PER_HOUR,
            limit_usd=10.0,  # $10 por hora
            action=BudgetAction.WARN,
            description="Límite por hora para operaciones continuas",
            is_system_policy=True,
            created_by="system"
        ))
        
        # Política por día
        self.add_policy(BudgetPolicy(
            name="daily_limit",
            period=BudgetPeriod.PER_DAY,
            limit_usd=50.0,  # $50 por día
            action=BudgetAction.BLOCK,
            description="Límite diario crítico",
            is_system_policy=True,
            created_by="system"
        ))
        
        # Política por operación
        self.add_policy(BudgetPolicy(
            name="per_operation",
            period=BudgetPeriod.PER_OPERATION,
            limit_usd=0.10,  # $0.10 por operación
            action=BudgetAction.WARN,
            description="Límite por operación individual",
            is_system_policy=True,
            created_by="system"
        ))
    
    def add_user_profile(self, user_profile: UserProfile):
        """Agrega o actualiza un perfil de usuario."""
        self.user_profiles[user_profile.user_id] = user_profile
        
        # Mantener lista de usuarios admin
        if user_profile.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            self.admin_users.add(user_profile.user_id)
        else:
            self.admin_users.discard(user_profile.user_id)
        
        log.info("user_profile.added", 
                user_id=user_profile.user_id,
                username=user_profile.username,
                role=user_profile.role.value)
    
    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Obtiene el perfil de un usuario."""
        return self.user_profiles.get(user_id)
    
    def is_admin_user(self, user_id: str) -> bool:
        """Verifica si un usuario es administrador."""
        return user_id in self.admin_users
    
    def can_user_modify_policy(self, user_id: str, policy_name: str) -> bool:
        """Verifica si un usuario puede modificar una política específica."""
        user_profile = self.get_user_profile(user_id)
        if not user_profile:
            return False
        
        policy = self.get_policy(policy_name)
        if not policy:
            return False
        
        return policy.can_be_modified_by(user_profile)
    
    def add_policy(self, policy: BudgetPolicy, user_id: str = None):
        """Agrega una nueva política de presupuesto."""
        # Verificar permisos si se especifica usuario
        if user_id:
            user_profile = self.get_user_profile(user_id)
            if not user_profile or not user_profile.can_modify_budgets():
                raise PermissionError(f"Usuario {user_id} no tiene permisos para crear políticas")
            
            policy.created_by = user_id
        
        self.policies[policy.name] = policy
        log.info("budget_policy.added", 
                policy_name=policy.name, 
                limit_usd=policy.limit_usd,
                period=policy.period.value,
                created_by=policy.created_by)
    
    def remove_policy(self, policy_name: str, user_id: str):
        """Elimina una política de presupuesto."""
        if not self.can_user_modify_policy(user_id, policy_name):
            raise PermissionError(f"Usuario {user_id} no tiene permisos para eliminar la política {policy_name}")
        
        if policy_name in self.policies:
            policy = self.policies[policy_name]
            if policy.is_system_policy:
                raise ValueError(f"No se puede eliminar la política del sistema: {policy_name}")
            
            del self.policies[policy_name]
            log.info("budget_policy.removed", 
                    policy_name=policy_name,
                    removed_by=user_id)
    
    def modify_policy(self, policy_name: str, user_id: str, **modifications):
        """Modifica una política de presupuesto existente."""
        if not self.can_user_modify_policy(user_id, policy_name):
            raise PermissionError(f"Usuario {user_id} no tiene permisos para modificar la política {policy_name}")
        
        policy = self.get_policy(policy_name)
        if not policy:
            raise ValueError(f"Política {policy_name} no encontrada")
        
        # Aplicar modificaciones
        for field, value in modifications.items():
            if hasattr(policy, field) and field not in ['name', 'is_system_policy']:
                setattr(policy, field, value)
        
        # Actualizar metadatos de modificación
        policy.modified_by = user_id
        policy.modified_at = datetime.now()
        
        log.info("budget_policy.modified",
                policy_name=policy_name,
                modified_by=user_id,
                modifications=list(modifications.keys()))
        
        return policy
    
    def get_policy(self, policy_name: str) -> Optional[BudgetPolicy]:
        """Obtiene una política por nombre."""
        return self.policies.get(policy_name)
    
    def check_budget(self, 
                    cost_usd: float, 
                    operation_name: str = "unknown",
                    user_id: Optional[str] = None,
                    session_id: Optional[str] = None,
                    policy_name: str = "default_episode") -> Dict[str, Any]:
        """
        Verifica si una operación puede proceder según el presupuesto.
        
        Returns:
            Dict con resultado de la verificación:
            - allowed: bool - Si la operación puede proceder
            - action: BudgetAction - Acción recomendada
            - message: str - Mensaje explicativo
            - usage_percentage: float - Porcentaje de uso actual
            - remaining_usd: float - Presupuesto restante
        """
        
        policy = self.get_policy(policy_name)
        if not policy:
            log.warning("budget_policy.not_found", 
                       policy_name=policy_name, 
                       operation=operation_name)
            return {
                "allowed": True,  # Sin política = permitir
                "action": BudgetAction.WARN,
                "message": f"Política '{policy_name}' no encontrada",
                "usage_percentage": 0.0,
                "remaining_usd": float('inf')
            }
        
        # Obtener uso actual según el período
        usage_key = self._get_usage_key(policy.period, user_id, session_id)
        current_usage = self._get_or_create_usage(usage_key, policy.period)
        
        # Verificar límites
        soft_exceeded = current_usage.is_soft_limit_exceeded(policy.soft_limit_usd)
        hard_exceeded = current_usage.is_soft_limit_exceeded(policy.limit_usd)
        
        # Calcular métricas
        usage_percentage = current_usage.get_usage_percentage(policy.limit_usd)
        remaining_usd = max(0, policy.limit_usd - current_usage.current_usd)
        
        # Determinar acción
        if hard_exceeded:
            action = policy.action
            allowed = action != BudgetAction.BLOCK
            message = f"Presupuesto excedido: ${current_usage.current_usd:.4f} / ${policy.limit_usd:.4f}"
            
            # Generar alerta crítica
            self._generate_budget_alert(policy, current_usage, "hard_limit_exceeded")
            
        elif soft_exceeded:
            action = BudgetAction.WARN
            allowed = True
            message = f"Límite suave alcanzado: ${current_usage.current_usd:.4f} / ${policy.soft_limit_usd:.4f}"
            
            # Generar advertencia
            if policy.notify_on_soft_limit:
                self._generate_budget_alert(policy, current_usage, "soft_limit_warning")
        else:
            action = BudgetAction.WARN
            allowed = True
            message = f"Presupuesto OK: ${current_usage.current_usd:.4f} / ${policy.limit_usd:.4f}"
        
        # Registrar la operación si está permitida
        if allowed:
            current_usage.add_operation(cost_usd, 0, operation_name)  # tokens se agregan después
        
        result = {
            "allowed": allowed,
            "action": action,
            "message": message,
            "usage_percentage": usage_percentage,
            "remaining_usd": remaining_usd,
            "policy_name": policy_name,
            "current_usage_usd": current_usage.current_usd,
            "limit_usd": policy.limit_usd
        }
        
        log.info("budget_check.completed",
                operation=operation_name,
                cost_usd=cost_usd,
                allowed=allowed,
                action=action.value,
                usage_percentage=usage_percentage)
        
        return result
    
    def _get_usage_key(self, period: BudgetPeriod, user_id: Optional[str], session_id: Optional[str]) -> str:
        """Genera la clave para el uso del presupuesto."""
        if period == BudgetPeriod.PER_OPERATION:
            return f"operation_{uuid.uuid4().hex[:8]}"
        elif period == BudgetPeriod.PER_EPISODE:
            return f"episode_{uuid.uuid4().hex[:8]}"
        elif period == BudgetPeriod.PER_HOUR:
            hour_start = datetime.now().replace(minute=0, second=0, microsecond=0)
            return f"hour_{hour_start.isoformat()}"
        elif period == BudgetPeriod.PER_DAY:
            day_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            return f"day_{day_start.isoformat()}"
        elif period == BudgetPeriod.PER_WEEK:
            # Lunes de la semana actual
            today = datetime.now()
            monday = today - timedelta(days=today.weekday())
            week_start = monday.replace(hour=0, minute=0, second=0, microsecond=0)
            return f"week_{week_start.isoformat()}"
        elif period == BudgetPeriod.PER_MONTH:
            month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            return f"month_{month_start.isoformat()}"
        
        return f"unknown_{uuid.uuid4().hex[:8]}"
    
    def _get_or_create_usage(self, key: str, period: BudgetPeriod) -> BudgetUsage:
        """Obtiene o crea un registro de uso del presupuesto."""
        if key not in self.usage:
            # Determinar cuándo empezó el período
            if period == BudgetPeriod.PER_OPERATION:
                period_start = datetime.now()
            elif period == BudgetPeriod.PER_EPISODE:
                period_start = datetime.now()
            elif period == BudgetPeriod.PER_HOUR:
                period_start = datetime.now().replace(minute=0, second=0, microsecond=0)
            elif period == BudgetPeriod.PER_DAY:
                period_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == BudgetPeriod.PER_WEEK:
                today = datetime.now()
                monday = today - timedelta(days=today.weekday())
                period_start = monday.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == BudgetPeriod.PER_MONTH:
                period_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                period_start = datetime.now()
            
            self.usage[key] = BudgetUsage(period_start=period_start)
        
        return self.usage[key]
    
    def _generate_budget_alert(self, policy: BudgetPolicy, usage: BudgetUsage, alert_type: str):
        """Genera una alerta de presupuesto."""
        alert = {
            "id": str(uuid.uuid4()),
            "type": "budget_alert",
            "severity": "critical" if alert_type == "hard_limit_exceeded" else "warning",
            "policy_name": policy.name,
            "alert_type": alert_type,
            "current_usage_usd": usage.current_usd,
            "limit_usd": policy.limit_usd,
            "usage_percentage": usage.get_usage_percentage(policy.limit_usd),
            "timestamp": datetime.now().isoformat(),
            "message": f"Presupuesto {policy.name}: {alert_type.replace('_', ' ')}"
        }
        
        # Agregar a las alertas del usuario
        usage.alerts_generated.append(alert["id"])
        
        # Ejecutar callbacks
        for callback in self.budget_callbacks:
            try:
                callback(alert)
            except Exception as e:
                log.error("budget_callback.error", 
                         callback=str(callback), 
                         error=str(e))
        
        log.warning("budget_alert.generated",
                   alert_id=alert["id"],
                   policy_name=policy.name,
                   alert_type=alert_type,
                   usage_percentage=alert["usage_percentage"])
    
    def get_budget_summary(self, 
                          user_id: Optional[str] = None,
                          session_id: Optional[str] = None) -> Dict[str, Any]:
        """Obtiene un resumen del estado del presupuesto."""
        
        summary = {
            "policies": {},
            "current_usage": {},
            "alerts": [],
            "total_cost_usd": 0.0,
            "total_operations": 0
        }
        
        # Resumen de políticas
        for policy_name, policy in self.policies.items():
            summary["policies"][policy_name] = {
                "period": policy.period.value,
                "limit_usd": policy.limit_usd,
                "soft_limit_usd": policy.soft_limit_usd,
                "action": policy.action.value,
                "description": policy.description
            }
        
        # Resumen de uso actual
        for key, usage in self.usage.items():
            # Encontrar la política correspondiente
            policy_name = "unknown"
            for p_name, p in self.policies.items():
                if p.period.value in key:
                    policy_name = p_name
                    break
            
            summary["current_usage"][key] = {
                "policy_name": policy_name,
                "period_start": usage.period_start.isoformat(),
                "current_usd": usage.current_usd,
                "operations_count": usage.operations_count,
                "total_tokens": usage.total_tokens,
                "alerts_count": len(usage.alerts_generated)
            }
            
            summary["total_cost_usd"] += usage.current_usd
            summary["total_operations"] += usage.operations_count
        
        # Alertas recientes
        for usage in self.usage.values():
            summary["alerts"].extend(usage.alerts_generated)
        
        return summary
    
    def reset_budgets(self, 
                     user_id: Optional[str] = None,
                     session_id: Optional[str] = None):
        """Resetea los presupuestos (útil para testing)."""
        if user_id is None and session_id is None:
            # Resetear todos
            self.usage.clear()
            self.user_budgets.clear()
            self.session_budgets.clear()
            log.info("budget_manager.reset_all")
        else:
            # Resetear específicos
            if user_id:
                self.user_budgets[user_id].clear()
            if session_id:
                self.session_budgets[session_id].clear()
            log.info("budget_manager.reset_specific", 
                    user_id=user_id, 
                    session_id=session_id)
    
    def add_budget_callback(self, callback: callable):
        """Agrega un callback para notificaciones de presupuesto."""
        self.budget_callbacks.append(callback)
        log.info("budget_callback.added", callback=str(callback))


# Instancia global del gestor de presupuestos
budget_manager = BudgetManager()


# Funciones de conveniencia para uso directo
def check_budget(cost_usd: float, 
                operation_name: str = "unknown",
                user_id: Optional[str] = None,
                session_id: Optional[str] = None,
                policy_name: str = "default_episode") -> Dict[str, Any]:
    """Verifica si una operación puede proceder según el presupuesto."""
    return budget_manager.check_budget(cost_usd, operation_name, user_id, session_id, policy_name)


def get_budget_summary(user_id: Optional[str] = None,
                      session_id: Optional[str] = None) -> Dict[str, Any]:
    """Obtiene un resumen del estado del presupuesto."""
    return budget_manager.get_budget_summary(user_id, session_id)


def add_budget_policy(policy: BudgetPolicy, user_id: str = None):
    """Agrega una nueva política de presupuesto."""
    budget_manager.add_policy(policy, user_id)


def reset_budgets(user_id: Optional[str] = None, session_id: Optional[str] = None):
    """Resetea los presupuestos."""
    budget_manager.reset_budgets(user_id, session_id)


def add_user_profile(user_id: str, username: str, role: UserRole = UserRole.USER):
    """Agrega o actualiza un perfil de usuario."""
    user_profile = UserProfile(user_id=user_id, username=username, role=role)
    budget_manager.add_user_profile(user_profile)
    return user_profile


def get_user_profile(user_id: str) -> Optional[UserProfile]:
    """Obtiene el perfil de un usuario."""
    return budget_manager.get_user_profile(user_id)


def is_admin_user(user_id: str) -> bool:
    """Verifica si un usuario es administrador."""
    return budget_manager.is_admin_user(user_id)


def can_user_modify_policy(user_id: str, policy_name: str) -> bool:
    """Verifica si un usuario puede modificar una política específica."""
    return budget_manager.can_user_modify_policy(user_id, policy_name)


def modify_budget_policy(policy_name: str, user_id: str, **modifications):
    """Modifica una política de presupuesto existente."""
    return budget_manager.modify_policy(policy_name, user_id, **modifications)


def remove_budget_policy(policy_name: str, user_id: str):
    """Elimina una política de presupuesto."""
    return budget_manager.remove_policy(policy_name, user_id)


def parse_natural_language_budget(budget_text: str) -> Dict[str, Any]:
    """
    Parsea texto en lenguaje natural para crear políticas de presupuesto.
    
    Ejemplos de entrada:
    - "Quiero gastar máximo $5 por día"
    - "Mi presupuesto es $20 por semana"
    - "No quiero que una sola operación cueste más de $0.50"
    - "Límite de $100 por mes para este proyecto"
    
    Returns:
        Dict con información parseada para crear políticas
    """
    
    import re
    
    # Patrones para detectar cantidades y períodos
    amount_pattern = r'\$?(\d+(?:\.\d+)?)'
    period_patterns = {
        'per_operation': r'(?:operación|operation|vez|single|individual)',
        'per_episode': r'(?:episodio|episode|sesión|session)',
        'per_hour': r'(?:hora|hour|por hora|per hour)',
        'per_day': r'(?:día|day|diario|daily|por día|per day)',
        'per_week': r'(?:semana|week|semanal|weekly|por semana|per week)',
        'per_month': r'(?:mes|month|mensual|monthly|por mes|per month)'
    }
    
    action_patterns = {
        'warn': r'(?:advertencia|warning|avisar|notify)',
        'throttle': r'(?:reducir|throttle|lento|slow|controlar)',
        'block': r'(?:bloquear|block|parar|stop|prohibir)',
        'graceful_degradation': r'(?:degradar|degrade|calidad|quality)'
    }
    
    # Extraer cantidad
    amount_match = re.search(amount_pattern, budget_text.lower())
    if not amount_match:
        return {"error": "No se pudo detectar una cantidad válida"}
    
    amount = float(amount_match.group(1))
    
    # Detectar período
    detected_period = None
    for period_key, pattern in period_patterns.items():
        if re.search(pattern, budget_text.lower()):
            detected_period = period_key
            break
    
    if not detected_period:
        # Por defecto, asumir por episodio si no se especifica
        detected_period = 'per_episode'
    
    # Detectar acción
    detected_action = BudgetAction.WARN  # Por defecto
    for action_key, pattern in action_patterns.items():
        if re.search(pattern, budget_text.lower()):
            detected_action = BudgetAction(action_key)
            break
    
    # Generar nombre de política
    policy_name = f"user_{detected_period}_{int(amount * 100)}"
    
    # Crear descripción
    period_names = {
        'per_operation': 'por operación',
        'per_episode': 'por episodio',
        'per_hour': 'por hora',
        'per_day': 'por día',
        'per_week': 'por semana',
        'per_month': 'por mes'
    }
    
    description = f"Política del usuario: ${amount:.2f} {period_names[detected_period]}"
    
    return {
        "amount_usd": amount,
        "period": detected_period,
        "action": detected_action.value,
        "policy_name": policy_name,
        "description": description,
        "success": True
    }


def create_policy_from_natural_language(budget_text: str, 
                                       user_id: Optional[str] = None,
                                       session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Crea una política de presupuesto a partir de texto en lenguaje natural.
    
    Args:
        budget_text: Texto descriptivo del presupuesto (ej: "Quiero gastar máximo $5 por día")
        user_id: ID del usuario (opcional)
        session_id: ID de la sesión (opcional)
    
    Returns:
        Dict con resultado de la creación de la política
    """
    
    # Verificar permisos si se especifica usuario
    if user_id:
        user_profile = get_user_profile(user_id)
        if not user_profile:
            return {
                "success": False,
                "error": f"Usuario {user_id} no encontrado"
            }
        
        if not user_profile.can_modify_budgets():
            return {
                "success": False,
                "error": f"Usuario {user_id} no tiene permisos para crear políticas de presupuesto. Solo los administradores pueden modificar presupuestos."
            }
    
    # Parsear el texto
    parsed = parse_natural_language_budget(budget_text)
    if not parsed.get("success"):
        return parsed
    
    try:
        # Crear la política
        policy = BudgetPolicy(
            name=parsed["policy_name"],
            period=BudgetPeriod(parsed["period"]),
            limit_usd=parsed["amount_usd"],
            action=BudgetAction(parsed["action"]),
            description=parsed["description"]
        )
        
        # Agregar la política
        add_budget_policy(policy, user_id)
        
        # Registrar en el log
        log.info("budget_policy.created_from_natural_language",
                user_id=user_id,
                session_id=session_id,
                budget_text=budget_text,
                policy_name=policy.name,
                limit_usd=policy.limit_usd,
                period=policy.period.value)
        
        return {
            "success": True,
            "policy_created": True,
            "policy_name": policy.name,
            "message": f"Política '{policy.name}' creada exitosamente",
            "details": {
                "limit_usd": policy.limit_usd,
                "period": policy.period.value,
                "action": policy.action.value,
                "description": policy.description
            }
        }
        
    except Exception as e:
        log.error("budget_policy.creation_error",
                 budget_text=budget_text,
                 error=str(e))
        return {
            "success": False,
            "error": f"Error al crear política: {str(e)}"
        }


def get_user_budget_summary(user_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Obtiene un resumen del presupuesto específico de un usuario.
    
    Args:
        user_id: ID del usuario
        session_id: ID de la sesión (opcional)
    
    Returns:
        Dict con resumen del presupuesto del usuario
    """
    
    # Obtener resumen general
    general_summary = get_budget_summary(user_id, session_id)
    
    # Filtrar políticas del usuario
    user_policies = {}
    for name, policy in general_summary["policies"].items():
        if name.startswith("user_"):
            user_policies[name] = policy
    
    # Calcular estadísticas del usuario
    total_user_cost = 0.0
    total_user_operations = 0
    
    for key, usage in general_summary["current_usage"].items():
        if user_id in key or (session_id and session_id in key):
            total_user_cost += usage["current_usd"]
            total_user_operations += usage["operations_count"]
    
    return {
        "user_id": user_id,
        "session_id": session_id,
        "user_policies": user_policies,
        "total_user_cost_usd": total_user_cost,
        "total_user_operations": total_user_operations,
        "policies_count": len(user_policies),
        "general_summary": general_summary
    }


def suggest_budget_optimization(user_id: str, 
                               current_usage: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sugiere optimizaciones de presupuesto basadas en el uso actual.
    
    Args:
        user_id: ID del usuario
        session_id: ID de la sesión (opcional)
        current_usage: Uso actual del usuario
    
    Returns:
        Dict con sugerencias de optimización
    """
    
    suggestions = []
    
    # Analizar uso por período
    for period, usage in current_usage.items():
        if "hour" in period and usage["current_usd"] > 5.0:
            suggestions.append({
                "type": "high_hourly_usage",
                "message": f"Uso por hora alto: ${usage['current_usd']:.2f}. Considera límites más estrictos.",
                "recommendation": "Agregar política por hora con límite de $3-4"
            })
        
        elif "day" in period and usage["current_usd"] > 20.0:
            suggestions.append({
                "type": "high_daily_usage",
                "message": f"Uso diario alto: ${usage['current_usd']:.2f}. Considera límites diarios.",
                "recommendation": "Agregar política diaria con límite de $15-20"
            })
    
    # Analizar operaciones costosas
    expensive_operations = []
    for usage in current_usage.values():
        for operation in usage.get("operations", []):
            if operation.get("cost_usd", 0) > 0.10:  # Más de $0.10
                expensive_operations.append({
                    "operation": operation.get("operation", "unknown"),
                    "cost_usd": operation.get("cost_usd", 0),
                    "timestamp": operation.get("timestamp", "unknown")
                })
    
    if expensive_operations:
        suggestions.append({
            "type": "expensive_operations",
            "message": f"Se detectaron {len(expensive_operations)} operaciones costosas",
            "recommendation": "Considera límites por operación más estrictos",
            "examples": expensive_operations[:3]  # Solo las primeras 3
        })
    
    return {
        "user_id": user_id,
        "suggestions_count": len(suggestions),
        "suggestions": suggestions,
        "has_expensive_operations": len(expensive_operations) > 0,
        "total_expensive_operations": len(expensive_operations)
    }
