"""
Phase 2 Intelligence Endpoints for Healer Agent

Adds AI diagnostics and life-plan knowledge to the healer.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)


class DiagnoseRequest(BaseModel):
    """Request for AI diagnostics"""
    agent_name: str
    symptoms: List[str]
    logs: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class FailureModeInfo(BaseModel):
    """Information about a known failure mode"""
    mode_id: str
    description: str
    severity: str
    expected_mttr_minutes: float
    recovery_steps: List[str]
    confidence: float


def add_intelligence_endpoints(
    app: FastAPI,
    life_plans_loader,
    ai_diagnostics
):
    """
    Add Phase 2 intelligence endpoints to healer-agent.
    
    Requires:
    - LifePlansLoader instance
    - AIDiagnostics instance
    """
    
    @app.post("/diagnose")
    async def diagnose_service(request: DiagnoseRequest):
        """
        AI-powered root cause analysis.
        
        Combines:
        1. Known failure modes from life-plans
        2. AI analysis of symptoms
        3. Recommended recovery steps
        """
        logger.info(f"Diagnosing {request.agent_name}: {request.symptoms}")
        
        # Step 1: Check known failure modes
        matching_modes = life_plans_loader.find_matching_failure_modes(
            request.agent_name,
            request.symptoms
        )
        
        if matching_modes:
            # Known issue - use playbook
            best_mode = matching_modes[0]
            return {
                "diagnosis": "known_failure_mode",
                "confidence": 0.95,
                "failure_mode": best_mode.mode_id,
                "description": best_mode.description,
                "severity": best_mode.severity,
                "estimated_recovery_time_minutes": best_mode.expected_mttr_minutes,
                "recovery_steps": [
                    step.description for step in best_mode.recovery_steps
                ],
                "source": "life-plans"
            }
        
        # Step 2: Use AI diagnostics for unknown issues
        ai_result = await ai_diagnostics.diagnose(
            request.agent_name,
            request.symptoms,
            request.logs,
            request.context
        )
        
        return {
            "diagnosis": "ai_analysis",
            "confidence": ai_result["confidence"],
            "root_cause": ai_result["root_cause"],
            "recommended_fix": ai_result["recommended_fix"],
            "steps": ai_result["steps"],
            "estimated_recovery_time_minutes": ai_result[
                "estimated_resolution_time_minutes"
            ],
            "escalate_to_human": ai_result["escalate_to_human"],
            "source": "ai-diagnostics"
        }
    
    
    @app.get("/failure-modes/{agent_name}")
    async def get_failure_modes(agent_name: str):
        """
        Get all known failure modes for an agent.
        
        Useful for understanding what can go wrong and how to fix it.
        """
        modes = life_plans_loader.get_failure_modes(agent_name)
        
        return {
            "agent": agent_name,
            "failure_modes": [
                {
                    "mode_id": mode.mode_id,
                    "description": mode.description,
                    "symptoms": mode.symptoms,
                    "severity": mode.severity,
                    "expected_mttr_minutes": mode.expected_mttr_minutes,
                    "recovery_steps": [
                        step.description for step in mode.recovery_steps
                    ]
                }
                for mode in modes
            ],
            "total": len(modes)
        }
    
    
    @app.get("/slos/{agent_name}")
    async def get_agent_slos(agent_name: str):
        """
        Get SLOs (Service Level Objectives) for an agent.
        
        Useful for understanding acceptable performance/availability.
        """
        plan = life_plans_loader.get_plan(agent_name)
        if not plan:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        return {
            "agent": agent_name,
            "slos": plan.performance_slos,
            "metrics": [
                {
                    "name": m.get("name"),
                    "prometheus_query": m.get("prometheus_query"),
                    "alert_if": m.get("alert_if")
                }
                for m in plan.metrics_to_monitor
            ]
        }
    
    
    @app.get("/playbook/{agent_name}/{playbook_name}")
    async def get_playbook(agent_name: str, playbook_name: str):
        """
        Get on-call playbook for specific alert/situation.
        
        Example: /playbook/healer-agent/alert_service_unhealthy
        """
        playbook = life_plans_loader.get_playbook(agent_name, playbook_name)
        if not playbook:
            raise HTTPException(status_code=404, detail="Playbook not found")
        
        return {
            "agent": agent_name,
            "playbook": playbook_name,
            "steps": playbook
        }
    
    
    @app.get("/life-plan/{agent_name}")
    async def get_life_plan(agent_name: str):
        """
        Get complete life-plan for an agent.
        
        Includes purpose, dependencies, SLOs, metrics, and failure modes.
        """
        plan = life_plans_loader.get_plan(agent_name)
        if not plan:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        return {
            "name": plan.name,
            "version": plan.version,
            "purpose": plan.purpose,
            "critical_dependencies": plan.critical_dependencies,
            "performance_slos": plan.performance_slos,
            "failure_modes": [
                {
                    "mode_id": mode.mode_id,
                    "description": mode.description,
                    "severity": mode.severity
                }
                for mode in plan.failure_modes
            ],
            "metrics": plan.metrics_to_monitor,
            "playbooks": list(plan.on_call_playbook.keys())
        }
    
    
    @app.get("/all-metrics")
    async def get_all_metrics():
        """
        Get all metrics that should be monitored across the entire system.
        
        Useful for setting up Prometheus dashboards.
        """
        metrics = life_plans_loader.get_all_metrics()
        
        # Group by type
        latency_metrics = [m for m in metrics if "latency" in m.get("name", "").lower()]
        reliability_metrics = [
            m for m in metrics if "reliability" in m.get("name", "").lower()
        ]
        health_metrics = [m for m in metrics if "health" in m.get("name", "").lower()]
        other_metrics = [
            m for m in metrics
            if m not in latency_metrics + reliability_metrics + health_metrics
        ]
        
        return {
            "total": len(metrics),
            "by_type": {
                "latency": latency_metrics,
                "reliability": reliability_metrics,
                "health": health_metrics,
                "other": other_metrics
            },
            "prometheus_targets": [
                {
                    "job_name": f"healer-{m.get('name', 'metric')}",
                    "metrics_path": "/metrics",
                    "static_configs": [{"targets": ["localhost:8010"]}],
                    "metric_relabel_configs": [
                        {
                            "source_labels": ["__name__"],
                            "regex": m.get("prometheus_query", ".*"),
                            "action": "keep"
                        }
                    ]
                }
                for m in metrics[:5]  # First 5 as examples
            ]
        }
    
    
    return {
        "diagnose_service": diagnose_service,
        "get_failure_modes": get_failure_modes,
        "get_agent_slos": get_agent_slos,
        "get_playbook": get_playbook,
        "get_life_plan": get_life_plan,
        "get_all_metrics": get_all_metrics,
    }
