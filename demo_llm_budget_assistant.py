#!/usr/bin/env python3
"""
Demo del Asistente LLM de Presupuesto.

Este script simula cómo un LLM usaría el sistema de gestión de presupuesto
para interpretar las solicitudes del usuario y crear políticas automáticamente.
"""

import time
from src.core.budget_management import (
    get_budget_summary, reset_budgets,
    create_policy_from_natural_language,
    get_user_budget_summary
)
from src.tools.budget_monitor import BudgetMonitorTool, BudgetMonitorIn


class LLMBudgetAssistant:
    """
    Simula un asistente LLM que ayuda a los usuarios a gestionar presupuestos.
    """
    
    def __init__(self):
        self.budget_tool = BudgetMonitorTool()
        self.user_id = "demo_user_123"
        self.session_id = "session_alpha"
    
    def process_user_request(self, user_request: str) -> dict:
        """
        Procesa una solicitud del usuario y crea políticas de presupuesto.
        
        Args:
            user_request: Solicitud del usuario en lenguaje natural
        
        Returns:
            Dict con la respuesta del asistente
        """
        
        print(f"👤 Usuario: {user_request}")
        print("🤖 LLM Asistente procesando...")
        
        # 1. Analizar la solicitud del usuario
        analysis = self._analyze_user_request(user_request)
        
        # 2. Crear política de presupuesto
        if analysis["can_create_policy"]:
            policy_result = self._create_budget_policy(user_request)
            analysis["policy_created"] = policy_result
        else:
            analysis["policy_created"] = None
        
        # 3. Generar recomendaciones
        recommendations = self._generate_recommendations(analysis)
        analysis["recommendations"] = recommendations
        
        # 4. Formatear respuesta
        response = self._format_response(analysis)
        
        return response
    
    def _analyze_user_request(self, user_request: str) -> dict:
        """Analiza la solicitud del usuario para determinar si se puede crear una política."""
        
        # Palabras clave que indican solicitud de presupuesto
        budget_keywords = [
            "presupuesto", "budget", "gastar", "spend", "costo", "cost",
            "límite", "limit", "máximo", "maximum", "quiero", "want",
            "día", "day", "semana", "week", "mes", "month", "hora", "hour"
        ]
        
        # Verificar si es una solicitud de presupuesto
        is_budget_request = any(keyword in user_request.lower() for keyword in budget_keywords)
        
        # Detectar si menciona cantidades monetarias
        has_amount = any(char.isdigit() for char in user_request)
        
        return {
            "user_request": user_request,
            "is_budget_request": is_budget_request,
            "has_amount": has_amount,
            "can_create_policy": is_budget_request and has_amount,
            "analysis": {
                "keywords_found": [k for k in budget_keywords if k in user_request.lower()],
                "has_numbers": has_amount
            }
        }
    
    def _create_budget_policy(self, user_request: str) -> dict:
        """Crea una política de presupuesto basada en la solicitud del usuario."""
        
        try:
            result = create_policy_from_natural_language(
                budget_text=user_request,
                user_id=self.user_id,
                session_id=self.session_id
            )
            
            if result.get("success"):
                print(f"  ✅ Política creada: {result['policy_name']}")
                return result
            else:
                print(f"  ❌ Error al crear política: {result.get('error')}")
                return result
                
        except Exception as e:
            print(f"  ❌ Excepción al crear política: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_recommendations(self, analysis: dict) -> list:
        """Genera recomendaciones basadas en el análisis."""
        
        recommendations = []
        
        if analysis["can_create_policy"]:
            recommendations.append({
                "type": "policy_created",
                "message": "✅ Se creó una nueva política de presupuesto",
                "action": "La política está activa y se aplicará automáticamente"
            })
            
            # Recomendaciones adicionales
            recommendations.append({
                "type": "monitoring",
                "message": "📊 Monitorea tu presupuesto regularmente",
                "action": "Usa 'budget_monitor' para ver el estado actual"
            })
            
            recommendations.append({
                "type": "optimization",
                "message": "💡 Considera ajustar límites según tu uso",
                "action": "Puedes modificar políticas existentes o crear nuevas"
            })
        
        elif analysis["is_budget_request"]:
            recommendations.append({
                "type": "clarification",
                "message": "❓ Necesito más detalles sobre tu presupuesto",
                "action": "Especifica una cantidad y período (ej: '$5 por día')"
            })
        
        else:
            recommendations.append({
                "type": "general",
                "message": "💭 ¿Te gustaría configurar un presupuesto?",
                "action": "Puedes decir algo como 'Quiero gastar máximo $10 por día'"
            })
        
        return recommendations
    
    def _format_response(self, analysis: dict) -> dict:
        """Formatea la respuesta final del asistente."""
        
        response = {
            "assistant_response": {
                "summary": self._generate_summary(analysis),
                "details": analysis,
                "next_steps": self._suggest_next_steps(analysis)
            }
        }
        
        return response
    
    def _generate_summary(self, analysis: dict) -> str:
        """Genera un resumen de la respuesta."""
        
        if analysis["can_create_policy"] and analysis["policy_created"]:
            policy = analysis["policy_created"]
            return f"✅ He configurado tu presupuesto: {policy['details']['description']}"
        
        elif analysis["is_budget_request"]:
            return "❓ Entiendo que quieres configurar un presupuesto, pero necesito más detalles."
        
        else:
            return "💭 ¿Te gustaría que te ayude a configurar un presupuesto para controlar tus gastos?"
    
    def _suggest_next_steps(self, analysis: dict) -> list:
        """Sugiere próximos pasos al usuario."""
        
        steps = []
        
        if analysis["can_create_policy"]:
            steps.append("📊 Revisa el estado de tu presupuesto")
            steps.append("🔧 Ajusta límites si es necesario")
            steps.append("📈 Monitorea tu uso regularmente")
        else:
            steps.append("💬 Describe tu presupuesto en detalle")
            steps.append("💰 Especifica cantidades y períodos")
            steps.append("🎯 Define qué hacer cuando se excedan los límites")
        
        return steps


def demonstrate_llm_assistant():
    """Demuestra cómo el LLM asistente procesa solicitudes de presupuesto."""
    
    print("🤖 DEMO: Asistente LLM de Presupuesto")
    print("=" * 50)
    
    # Crear asistente
    assistant = LLMBudgetAssistant()
    
    # Ejemplos de solicitudes de usuarios
    user_requests = [
        "Quiero gastar máximo $5 por día en este proyecto",
        "Mi presupuesto es $20 por semana",
        "No quiero que una sola operación cueste más de $0.50",
        "Ayúdame con mi presupuesto",
        "Quiero controlar mis gastos",
        "Límite de $100 por mes para este proyecto"
    ]
    
    print("📝 Procesando solicitudes de usuarios...\n")
    
    for i, request in enumerate(user_requests, 1):
        print(f"🔍 Solicitud {i}:")
        
        # Procesar solicitud
        response = assistant.process_user_request(request)
        
        # Mostrar respuesta
        print(f"  🤖 Respuesta: {response['assistant_response']['summary']}")
        
        # Mostrar recomendaciones
        if response['assistant_response'].get('recommendations'):
            print("  💡 Recomendaciones:")
            for rec in response['assistant_response']['recommendations']:
                print(f"    - {rec['message']}")
                print(f"      → {rec['action']}")
        
        # Mostrar próximos pasos
        if response['assistant_response'].get('next_steps'):
            print("  🚀 Próximos pasos:")
            for step in response['assistant_response']['next_steps']:
                print(f"    - {step}")
        
        print()
        time.sleep(1)  # Pausa para mejor legibilidad
    
    # Mostrar resumen final
    print("📊 RESUMEN FINAL:")
    user_summary = get_user_budget_summary(assistant.user_id, assistant.session_id)
    
    print(f"  👤 Usuario: {assistant.user_id}")
    print(f"  📱 Sesión: {assistant.session_id}")
    print(f"  💰 Políticas creadas: {user_summary['policies_count']}")
    print(f"  📈 Costo total: ${user_summary['total_user_cost_usd']:.4f}")
    print(f"  🔄 Operaciones totales: {user_summary['total_user_operations']}")
    
    if user_summary['user_policies']:
        print("  📋 Políticas activas:")
        for name, policy in user_summary['user_policies'].items():
            print(f"    - {name}: ${policy['limit_usd']:.2f} ({policy['period']})")


def main():
    """Función principal."""
    
    # Resetear presupuestos para demo limpia
    reset_budgets()
    
    try:
        demonstrate_llm_assistant()
        
        print("\n🎉 ¡Demo del Asistente LLM completado!")
        print("\n💡 Características demostradas:")
        print("  ✅ Interpretación de lenguaje natural")
        print("  ✅ Creación automática de políticas")
        print("  ✅ Recomendaciones inteligentes")
        print("  ✅ Gestión automática de presupuestos")
        print("  ✅ Interfaz conversacional natural")
        
    except Exception as e:
        print(f"\n❌ Error durante la demo: {e}")


if __name__ == "__main__":
    main()
