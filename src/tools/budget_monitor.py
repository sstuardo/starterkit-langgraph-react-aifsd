#!/usr/bin/env python3
"""
Herramienta de Monitoreo de Presupuesto.

Esta herramienta permite al agente:
- Consultar estado del presupuesto en tiempo real
- Ver políticas activas y límites
- Monitorear uso actual y tendencias
- Configurar alertas de presupuesto
- Ver estado del throttling automático
"""

from src.core.tool_interface import ToolInput, ToolOutput
from src.core.budget_management import (
    get_budget_summary, add_budget_policy, reset_budgets,
    BudgetPolicy, BudgetPeriod, BudgetAction
)
from src.core.throttling_service import get_throttling_summary, reset_throttling


class BudgetMonitorIn(ToolInput):
    """Input para la herramienta de monitoreo de presupuesto."""
    
    action: str = "summary"  # summary, policies, usage, alerts, throttling, configure, create_policy
    policy_name: str = None  # Política específica a consultar
    user_id: str = None      # ID de usuario para filtrado
    session_id: str = None   # ID de sesión para filtrado
    format: str = "summary"  # json, summary
    budget_text: str = None  # Texto en lenguaje natural para crear políticas
    natural_language_budget: str = None  # Alias para budget_text


class BudgetMonitorTool:
    """Herramienta de monitoreo de presupuesto para el agente."""
    
    name: str = "budget_monitor"
    description: str = (
        "Monitorea y gestiona presupuestos del sistema, políticas, "
        "uso actual y throttling automático. También puede crear políticas "
        "a partir de texto en lenguaje natural."
    )
    timeout_s: int = 10
    
    def __call__(self, args: BudgetMonitorIn) -> ToolOutput:
        """Ejecuta la acción de monitoreo de presupuesto solicitada."""
        
        try:
            # Determinar acción a ejecutar
            if args.action == "summary":
                content = self._get_budget_summary(args)
            elif args.action == "policies":
                content = self._get_policies_summary(args)
            elif args.action == "usage":
                content = self._get_usage_summary(args)
            elif args.action == "alerts":
                content = self._get_alerts_summary(args)
            elif args.action == "throttling":
                content = self._get_throttling_summary(args)
            elif args.action == "configure":
                content = self._get_configuration_help(args)
            elif args.action == "create_policy":
                content = self._create_policy_from_natural_language(args)
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
                content={"error": f"Error en monitoreo de presupuesto: {str(e)}"}
            )
    
    def _get_budget_summary(self, args: BudgetMonitorIn) -> dict:
        """Obtiene resumen general del presupuesto."""
        return get_budget_summary(args.user_id, args.session_id)
    
    def _get_policies_summary(self, args: BudgetMonitorIn) -> dict:
        """Obtiene resumen de políticas de presupuesto."""
        summary = get_budget_summary(args.user_id, args.session_id)
        
        policies = summary.get("policies", {})
        if args.policy_name and args.policy_name in policies:
            return {
                "policy": policies[args.policy_name],
                "policy_name": args.policy_name
            }
        
        return {
            "total_policies": len(policies),
            "policies": policies
        }
    
    def _get_usage_summary(self, args: BudgetMonitorIn) -> dict:
        """Obtiene resumen del uso del presupuesto."""
        summary = get_budget_summary(args.user_id, args.session_id)
        
        usage = summary.get("current_usage", {})
        if args.policy_name:
            # Filtrar por política específica
            filtered_usage = {
                k: v for k, v in usage.items() 
                if v.get("policy_name") == args.policy_name
            }
            return {
                "policy_name": args.policy_name,
                "usage": filtered_usage,
                "total_entries": len(filtered_usage)
            }
        
        return {
            "total_usage_entries": len(usage),
            "total_cost_usd": summary.get("total_cost_usd", 0.0),
            "total_operations": summary.get("total_operations", 0),
            "usage": usage
        }
    
    def _get_alerts_summary(self, args: BudgetMonitorIn) -> dict:
        """Obtiene resumen de alertas de presupuesto."""
        summary = get_budget_summary(args.user_id, args.session_id)
        
        alerts = summary.get("alerts", [])
        return {
            "total_alerts": len(alerts),
            "alerts": alerts[:10]  # Últimas 10 alertas
        }
    
    def _get_throttling_summary(self, args: BudgetMonitorIn) -> dict:
        """Obtiene resumen del estado del throttling."""
        return get_throttling_summary(args.policy_name)
    
    def _get_configuration_help(self, args: BudgetMonitorIn) -> dict:
        """Obtiene ayuda para configuración de presupuestos."""
        return {
            "help": "Configuración de Presupuestos",
            "available_periods": [p.value for p in BudgetPeriod],
            "available_actions": [a.value for a in BudgetAction],
            "example_policy": {
                "name": "custom_episode",
                "period": "per_episode",
                "limit_usd": 2.0,
                "action": "throttle",
                "description": "Límite personalizado por episodio"
            },
            "usage": "Usar add_budget_policy() para agregar políticas personalizadas"
        }
    
    def _create_policy_from_natural_language(self, args: BudgetMonitorIn) -> dict:
        """Crea una política de presupuesto a partir de texto en lenguaje natural."""
        
        # Usar budget_text o natural_language_budget
        budget_text = args.budget_text or args.natural_language_budget
        
        if not budget_text:
            return {
                "error": "Se requiere 'budget_text' o 'natural_language_budget' para crear políticas"
            }
        
        from src.core.budget_management import create_policy_from_natural_language
        
        result = create_policy_from_natural_language(
            budget_text=budget_text,
            user_id=args.user_id,
            session_id=args.session_id
        )
        
        return result
    
    def _format_summary(self, content: dict, action: str) -> dict:
        """Formatea el contenido en un resumen legible."""
        
        if action == "summary":
            return self._format_budget_summary(content)
        elif action == "policies":
            return self._format_policies_summary(content)
        elif action == "usage":
            return self._format_usage_summary(content)
        elif action == "alerts":
            return self._format_alerts_summary(content)
        elif action == "throttling":
            return self._format_throttling_summary(content)
        elif action == "configure":
            return self._format_configuration_summary(content)
        
        return content
    
    def _format_budget_summary(self, summary: dict) -> dict:
        """Formatea resumen general del presupuesto."""
        return {
            "summary": "Estado del Presupuesto",
            "total_policies": len(summary.get("policies", {})),
            "total_cost_usd": f"${summary.get('total_cost_usd', 0.0):.4f}",
            "total_operations": summary.get("total_operations", 0),
            "active_usage_entries": len(summary.get("current_usage", {})),
            "total_alerts": len(summary.get("alerts", []))
        }
    
    def _format_policies_summary(self, policies: dict) -> dict:
        """Formatea resumen de políticas."""
        if "policy" in policies:
            # Política específica
            policy = policies["policy"]
            return {
                "summary": f"Política: {policies['policy_name']}",
                "periodo": policy["period"],
                "limite_usd": f"${policy['limit_usd']:.4f}",
                "limite_suave_usd": f"${policy['soft_limit_usd']:.4f}",
                "accion": policy["action"],
                "descripcion": policy["description"]
            }
        else:
            # Todas las políticas
            return {
                "summary": "Políticas de Presupuesto",
                "total_policies": policies["total_policies"],
                "policies": [
                    {
                        "nombre": name,
                        "periodo": policy["period"],
                        "limite_usd": f"${policy['limit_usd']:.4f}",
                        "accion": policy["action"]
                    }
                    for name, policy in policies["policies"].items()
                ]
            }
    
    def _format_usage_summary(self, usage: dict) -> dict:
        """Formatea resumen de uso."""
        if "policy_name" in usage:
            # Uso de política específica
            return {
                "summary": f"Uso de Política: {usage['policy_name']}",
                "entradas": usage["total_entries"],
                "uso_detallado": usage["usage"]
            }
        else:
            # Uso general
            return {
                "summary": "Uso del Presupuesto",
                "total_entradas": usage["total_usage_entries"],
                "costo_total_usd": f"${usage['total_cost_usd']:.4f}",
                "total_operaciones": usage["total_operations"],
                "entradas_activas": len(usage["usage"])
            }
    
    def _format_alerts_summary(self, alerts: dict) -> dict:
        """Formatea resumen de alertas."""
        return {
            "summary": "Alertas de Presupuesto",
            "total_alertas": alerts["total_alerts"],
            "alertas_recientes": alerts["alerts"][:5]  # Solo las primeras 5
        }
    
    def _format_throttling_summary(self, throttling: dict) -> dict:
        """Formatea resumen de throttling."""
        return {
            "summary": "Estado del Throttling",
            "configuraciones": len(throttling.get("configs", {})),
            "operaciones_throttled": throttling.get("total_throttled_operations", 0),
            "tiempo_total_throttling_ms": f"{throttling.get('total_throttle_time_ms', 0.0):.1f}ms",
            "configuraciones_activas": [
                {
                    "operacion": name,
                    "throttles_consecutivos": config["consecutive_throttles"],
                    "tiempo_total_ms": f"{config['total_throttle_time_ms']:.1f}ms"
                }
                for name, config in throttling.get("configs", {}).items()
            ]
        }
    
    def _format_configuration_summary(self, config: dict) -> dict:
        """Formatea resumen de configuración."""
        return {
            "summary": "Ayuda de Configuración",
            "periodos_disponibles": config["available_periods"],
            "acciones_disponibles": config["available_actions"],
            "ejemplo_politica": config["example_policy"],
            "uso": config["usage"]
        }


# Instancia global de la herramienta
budget_monitor_tool = BudgetMonitorTool()
