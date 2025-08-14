#!/usr/bin/env python3
"""
Servicio de Throttling Automático.

Este módulo implementa:
- Control automático de velocidad basado en presupuesto
- Degradación gradual de calidad
- Rate limiting inteligente
- Backoff exponencial para operaciones costosas
"""

import time
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from collections import defaultdict

import structlog

from .budget_management import BudgetManager, BudgetPolicy, BudgetAction

# Configurar logging estructurado
log = structlog.get_logger()


class ThrottleLevel(Enum):
    """Niveles de throttling disponibles."""
    NONE = "none"           # Sin throttling
    LIGHT = "light"         # Throttling ligero
    MODERATE = "moderate"   # Throttling moderado
    HEAVY = "heavy"         # Throttling pesado
    BLOCKED = "blocked"     # Completamente bloqueado


@dataclass
class ThrottleConfig:
    """Configuración de throttling para una operación."""
    
    operation_name: str
    base_delay_ms: float = 0.0
    max_delay_ms: float = 5000.0  # 5 segundos máximo
    backoff_factor: float = 2.0   # Factor de backoff exponencial
    jitter_ms: float = 100.0      # Jitter para evitar thundering herd
    
    # Límites de calidad
    min_quality_factor: float = 0.1  # Calidad mínima (10%)
    quality_degradation_rate: float = 0.2  # Degradación por nivel
    
    # Métricas
    consecutive_throttles: int = 0
    total_throttle_time_ms: float = 0.0
    
    def get_delay_ms(self, throttle_level: ThrottleLevel) -> float:
        """Calcula el delay de throttling para un nivel dado."""
        if throttle_level == ThrottleLevel.NONE:
            return 0.0
        
        # Calcular delay base con backoff exponencial
        level_multiplier = {
            ThrottleLevel.LIGHT: 1,
            ThrottleLevel.MODERATE: 2,
            ThrottleLevel.HEAVY: 4,
            ThrottleLevel.BLOCKED: 8
        }
        
        multiplier = level_multiplier.get(throttle_level, 1)
        delay = self.base_delay_ms * (self.backoff_factor ** self.consecutive_throttles) * multiplier
        
        # Aplicar límite máximo
        delay = min(delay, self.max_delay_ms)
        
        # Agregar jitter para evitar sincronización
        jitter = random.uniform(-self.jitter_ms, self.jitter_ms)
        delay += jitter
        
        return max(0.0, delay)
    
    def get_quality_factor(self, throttle_level: ThrottleLevel) -> float:
        """Calcula el factor de calidad para un nivel de throttling."""
        if throttle_level == ThrottleLevel.NONE:
            return 1.0
        
        # Degradar calidad gradualmente
        degradation = self.quality_degradation_rate * self.consecutive_throttles
        
        # Aplicar límite mínimo
        quality = max(self.min_quality_factor, 1.0 - degradation)
        
        return quality


class ThrottlingService:
    """Servicio de throttling automático basado en presupuesto."""
    
    def __init__(self):
        """Inicializa el servicio de throttling."""
        self.budget_manager = BudgetManager()
        self.throttle_configs: Dict[str, ThrottleConfig] = {}
        self.operation_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.active_throttles: Dict[str, Dict[str, Any]] = {}
        
        # Callbacks para notificaciones
        self.throttle_callbacks: List[Callable] = []
        
        # Configurar configuraciones por defecto
        self._setup_default_configs()
        
        log.info("throttling_service.initialized")
    
    def _setup_default_configs(self):
        """Configura configuraciones de throttling por defecto."""
        
        # Configuración para operaciones de LLM
        self.add_throttle_config(ThrottleConfig(
            operation_name="llm_call",
            base_delay_ms=100.0,
            max_delay_ms=3000.0,
            backoff_factor=1.5,
            jitter_ms=50.0
        ))
        
        # Configuración para operaciones de herramientas
        self.add_throttle_config(ThrottleConfig(
            operation_name="tool_execution",
            base_delay_ms=50.0,
            max_delay_ms=1000.0,
            backoff_factor=1.3,
            jitter_ms=25.0
        ))
        
        # Configuración para operaciones de planificación
        self.add_throttle_config(ThrottleConfig(
            operation_name="planning",
            base_delay_ms=200.0,
            max_delay_ms=5000.0,
            backoff_factor=2.0,
            jitter_ms=100.0
        ))
    
    def add_throttle_config(self, config: ThrottleConfig):
        """Agrega una configuración de throttling."""
        self.throttle_configs[config.operation_name] = config
        log.info("throttle_config.added", 
                operation_name=config.operation_name,
                base_delay_ms=config.base_delay_ms)
    
    def get_throttle_config(self, operation_name: str) -> ThrottleConfig:
        """Obtiene la configuración de throttling para una operación."""
        return self.throttle_configs.get(operation_name, ThrottleConfig(operation_name))
    
    def should_throttle(self, 
                       operation_name: str,
                       cost_usd: float,
                       user_id: Optional[str] = None,
                       session_id: Optional[str] = None,
                       policy_name: str = "default_episode") -> Dict[str, Any]:
        """
        Determina si una operación debe ser throttled.
        
        Returns:
            Dict con información de throttling:
            - should_throttle: bool - Si debe aplicar throttling
            - throttle_level: ThrottleLevel - Nivel de throttling
            - delay_ms: float - Delay en milisegundos
            - quality_factor: float - Factor de calidad
            - reason: str - Razón del throttling
        """
        
        # Verificar presupuesto primero
        budget_check = self.budget_manager.check_budget(
            cost_usd, operation_name, user_id, session_id, policy_name
        )
        
        # Determinar nivel de throttling basado en la acción del presupuesto
        throttle_level = self._determine_throttle_level(budget_check)
        
        # Obtener configuración de throttling
        config = self.get_throttle_config(operation_name)
        
        # Calcular delay y calidad
        delay_ms = config.get_delay_ms(throttle_level)
        quality_factor = config.get_quality_factor(throttle_level)
        
        # Determinar si debe aplicar throttling
        should_throttle = throttle_level != ThrottleLevel.NONE
        
        # Generar razón del throttling
        reason = self._generate_throttle_reason(budget_check, throttle_level)
        
        result = {
            "should_throttle": should_throttle,
            "throttle_level": throttle_level.value,
            "delay_ms": delay_ms,
            "quality_factor": quality_factor,
            "reason": reason,
            "budget_check": budget_check,
            "operation_name": operation_name
        }
        
        # Registrar la decisión de throttling
        self._record_throttle_decision(operation_name, result)
        
        # Ejecutar callbacks si hay throttling
        if should_throttle:
            self._execute_throttle_callbacks(result)
        
        log.info("throttle_decision.made",
                operation=operation_name,
                should_throttle=should_throttle,
                throttle_level=throttle_level.value,
                delay_ms=delay_ms,
                reason=reason)
        
        return result
    
    def _determine_throttle_level(self, budget_check: Dict[str, Any]) -> ThrottleLevel:
        """Determina el nivel de throttling basado en la verificación de presupuesto."""
        
        action = budget_check.get("action")
        usage_percentage = budget_check.get("usage_percentage", 0.0)
        
        if action == BudgetAction.BLOCK:
            return ThrottleLevel.BLOCKED
        
        elif action == BudgetAction.THROTTLE:
            if usage_percentage >= 90:
                return ThrottleLevel.HEAVY
            elif usage_percentage >= 75:
                return ThrottleLevel.MODERATE
            elif usage_percentage >= 60:
                return ThrottleLevel.LIGHT
            else:
                return ThrottleLevel.NONE
        
        elif action == BudgetAction.WARN:
            if usage_percentage >= 80:
                return ThrottleLevel.LIGHT
            else:
                return ThrottleLevel.NONE
        
        else:
            return ThrottleLevel.NONE
    
    def _generate_throttle_reason(self, budget_check: Dict[str, Any], throttle_level: ThrottleLevel) -> str:
        """Genera una razón explicativa para el throttling."""
        
        action = budget_check.get("action")
        usage_percentage = budget_check.get("usage_percentage", 0.0)
        policy_name = budget_check.get("policy_name", "unknown")
        
        if throttle_level == ThrottleLevel.BLOCKED:
            return f"Operación bloqueada por política '{policy_name}' - presupuesto excedido"
        
        elif throttle_level == ThrottleLevel.HEAVY:
            return f"Throttling pesado - {usage_percentage:.1f}% del presupuesto usado"
        
        elif throttle_level == ThrottleLevel.MODERATE:
            return f"Throttling moderado - {usage_percentage:.1f}% del presupuesto usado"
        
        elif throttle_level == ThrottleLevel.LIGHT:
            return f"Throttling ligero - {usage_percentage:.1f}% del presupuesto usado"
        
        else:
            return "Sin throttling - presupuesto dentro de límites"
    
    def apply_throttling(self, 
                        operation_name: str,
                        cost_usd: float,
                        user_id: Optional[str] = None,
                        session_id: Optional[str] = None,
                        policy_name: str = "default_episode") -> Dict[str, Any]:
        """
        Aplica throttling a una operación.
        
        Returns:
            Dict con resultado del throttling aplicado.
        """
        
        # Verificar si debe aplicar throttling
        throttle_info = self.should_throttle(
            operation_name, cost_usd, user_id, session_id, policy_name
        )
        
        if not throttle_info["should_throttle"]:
            return {
                "throttling_applied": False,
                "delay_ms": 0.0,
                "quality_factor": 1.0,
                "message": "No se aplicó throttling"
            }
        
        # Aplicar delay si es necesario
        delay_ms = throttle_info["delay_ms"]
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)  # Convertir a segundos
        
        # Actualizar configuración de throttling
        config = self.get_throttle_config(operation_name)
        if throttle_info["throttle_level"] != ThrottleLevel.NONE:
            config.consecutive_throttles += 1
            config.total_throttle_time_ms += delay_ms
        
        # Registrar operación throttled
        self._record_throttled_operation(operation_name, throttle_info)
        
        result = {
            "throttling_applied": True,
            "delay_ms": delay_ms,
            "quality_factor": throttle_info["quality_factor"],
            "throttle_level": throttle_info["throttle_level"],
            "reason": throttle_info["reason"],
            "message": f"Throttling aplicado: {delay_ms:.1f}ms delay, calidad {throttle_info['quality_factor']:.2f}"
        }
        
        log.info("throttling.applied",
                operation=operation_name,
                delay_ms=delay_ms,
                quality_factor=throttle_info["quality_factor"],
                throttle_level=throttle_info["throttle_level"])
        
        return result
    
    def _record_throttle_decision(self, operation_name: str, decision: Dict[str, Any]):
        """Registra una decisión de throttling."""
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "operation_name": operation_name,
            "decision": decision.copy()
        }
        
        self.operation_history[operation_name].append(record)
        
        # Mantener solo las últimas 100 decisiones
        if len(self.operation_history[operation_name]) > 100:
            self.operation_history[operation_name] = self.operation_history[operation_name][-100:]
    
    def _record_throttled_operation(self, operation_name: str, throttle_info: Dict[str, Any]):
        """Registra una operación que fue throttled."""
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "operation_name": operation_name,
            "throttle_level": throttle_info["throttle_level"],
            "delay_ms": throttle_info["delay_ms"],
            "quality_factor": throttle_info["quality_factor"],
            "reason": throttle_info["reason"]
        }
        
        self.operation_history[operation_name].append(record)
    
    def _execute_throttle_callbacks(self, throttle_info: Dict[str, Any]):
        """Ejecuta callbacks de notificación de throttling."""
        
        for callback in self.throttle_callbacks:
            try:
                callback(throttle_info)
            except Exception as e:
                log.error("throttle_callback.error",
                         callback=str(callback),
                         error=str(e))
    
    def get_throttling_summary(self, operation_name: Optional[str] = None) -> Dict[str, Any]:
        """Obtiene un resumen del estado del throttling."""
        
        summary = {
            "configs": {},
            "operation_history": {},
            "active_throttles": {},
            "total_throttled_operations": 0,
            "total_throttle_time_ms": 0.0
        }
        
        # Resumen de configuraciones
        for name, config in self.throttle_configs.items():
            summary["configs"][name] = {
                "base_delay_ms": config.base_delay_ms,
                "max_delay_ms": config.max_delay_ms,
                "backoff_factor": config.backoff_factor,
                "consecutive_throttles": config.consecutive_throttles,
                "total_throttle_time_ms": config.total_throttle_time_ms
            }
        
        # Resumen de historial de operaciones
        if operation_name:
            if operation_name in self.operation_history:
                summary["operation_history"][operation_name] = self.operation_history[operation_name][-10:]  # Últimas 10
        else:
            for name, history in self.operation_history.items():
                summary["operation_history"][name] = history[-5:]  # Últimas 5 de cada operación
        
        # Estadísticas generales
        for config in self.throttle_configs.values():
            summary["total_throttled_operations"] += config.consecutive_throttles
            summary["total_throttle_time_ms"] += config.total_throttle_time_ms
        
        return summary
    
    def reset_throttling(self, operation_name: Optional[str] = None):
        """Resetea el estado del throttling."""
        
        if operation_name is None:
            # Resetear todo
            for config in self.throttle_configs.values():
                config.consecutive_throttles = 0
                config.total_throttle_time_ms = 0.0
            
            self.operation_history.clear()
            self.active_throttles.clear()
            
            log.info("throttling_service.reset_all")
        else:
            # Resetear operación específica
            if operation_name in self.throttle_configs:
                config = self.throttle_configs[operation_name]
                config.consecutive_throttles = 0
                config.total_throttle_time_ms = 0.0
            
            if operation_name in self.operation_history:
                self.operation_history[operation_name].clear()
            
            log.info("throttling_service.reset_operation", operation_name=operation_name)
    
    def add_throttle_callback(self, callback: Callable):
        """Agrega un callback para notificaciones de throttling."""
        self.throttle_callbacks.append(callback)
        log.info("throttle_callback.added", callback=str(callback))


# Instancia global del servicio de throttling
throttling_service = ThrottlingService()


# Funciones de conveniencia para uso directo
def should_throttle(operation_name: str,
                   cost_usd: float,
                   user_id: Optional[str] = None,
                   session_id: Optional[str] = None,
                   policy_name: str = "default_episode") -> Dict[str, Any]:
    """Determina si una operación debe ser throttled."""
    return throttling_service.should_throttle(
        operation_name, cost_usd, user_id, session_id, policy_name
    )


def apply_throttling(operation_name: str,
                    cost_usd: float,
                    user_id: Optional[str] = None,
                    session_id: Optional[str] = None,
                    policy_name: str = "default_episode") -> Dict[str, Any]:
    """Aplica throttling a una operación."""
    return throttling_service.apply_throttling(
        operation_name, cost_usd, user_id, session_id, policy_name
    )


def get_throttling_summary(operation_name: Optional[str] = None) -> Dict[str, Any]:
    """Obtiene un resumen del estado del throttling."""
    return throttling_service.get_throttling_summary(operation_name)


def reset_throttling(operation_name: Optional[str] = None):
    """Resetea el estado del throttling."""
    throttling_service.reset_throttling(operation_name)
