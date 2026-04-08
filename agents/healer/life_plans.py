"""
Life Plans Loader for Healer Agent

Reads YAML life-plans and extracts failure modes, recovery steps, and SLOs.
"""

import os
import yaml
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class RecoveryStep:
    """Single recovery action"""
    step_number: int
    description: str
    command: Optional[str] = None
    timeout_seconds: Optional[float] = None


@dataclass
class FailureMode:
    """Failure mode with recovery strategy"""
    mode_id: str
    description: str
    symptoms: List[str]
    recovery_steps: List[RecoveryStep] = field(default_factory=list)
    expected_mttr_minutes: float = 5.0
    user_impact: str = "DEGRADED"
    severity: str = "P2"
    
    def __hash__(self):
        return hash(self.mode_id)
    
    def __eq__(self, other):
        if not isinstance(other, FailureMode):
            return False
        return self.mode_id == other.mode_id


@dataclass
class AgentLifePlan:
    """Complete life plan for an agent"""
    name: str
    version: str
    purpose: str
    failure_modes: List[FailureMode] = field(default_factory=list)
    critical_dependencies: List[str] = field(default_factory=list)
    performance_slos: Dict[str, Any] = field(default_factory=dict)
    metrics_to_monitor: List[Dict[str, str]] = field(default_factory=list)
    on_call_playbook: Dict[str, Any] = field(default_factory=dict)


class LifePlansLoader:
    """Loads and manages agent life-plans from YAML files"""
    
    def __init__(self, life_plans_dir: str = "/app/../life-plans"):
        self.life_plans_dir = Path(life_plans_dir)
        self.plans: Dict[str, AgentLifePlan] = {}
        self.failure_mode_index: Dict[str, List[FailureMode]] = {}
        
    def load_all(self) -> Dict[str, AgentLifePlan]:
        """Load all YAML life-plans from directory"""
        if not self.life_plans_dir.exists():
            logger.warning(f"Life plans directory not found: {self.life_plans_dir}")
            return {}
        
        for yaml_file in self.life_plans_dir.glob("*.yaml"):
            try:
                self.load_plan(yaml_file)
            except Exception as e:
                logger.error(f"Failed to load {yaml_file}: {e}")
        
        logger.info(f"Loaded {len(self.plans)} life-plans")
        return self.plans
    
    def load_plan(self, file_path: Path) -> Optional[AgentLifePlan]:
        """Load single life-plan YAML file"""
        try:
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
            
            if not data:
                return None
            
            # Extract core fields
            identity = data.get('service_identity', {})
            name = identity.get('name', file_path.stem)
            version = identity.get('version', '1.0.0')
            purpose = identity.get('core_purpose', '')
            
            # Parse failure modes
            failure_modes = []
            for fm in data.get('failure_modes', []):
                failure_modes.append(self._parse_failure_mode(fm))
            
            # Parse critical dependencies
            deps = data.get('responsibility_matrix', {}).get('critical_dependencies', [])
            critical_dependencies = [d.split(' → ')[0] if ' → ' in d else d for d in deps]
            
            # Parse SLOs
            perf_slos = data.get('performance_slos', {})
            
            # Parse metrics
            metrics = data.get('metrics_to_monitor', [])
            
            # Parse playbook
            playbook = data.get('on_call_playbook', {})
            
            plan = AgentLifePlan(
                name=name,
                version=version,
                purpose=purpose,
                failure_modes=failure_modes,
                critical_dependencies=critical_dependencies,
                performance_slos=perf_slos,
                metrics_to_monitor=metrics,
                on_call_playbook=playbook
            )
            
            self.plans[name] = plan
            
            # Build failure mode index
            self.failure_mode_index[name] = failure_modes
            
            logger.info(f"Loaded life-plan for {name} (v{version}) with {len(failure_modes)} failure modes")
            return plan
            
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return None
    
    def _parse_failure_mode(self, data: Dict[str, Any]) -> FailureMode:
        """Parse single failure mode from YAML"""
        mode_id = data.get('mode_id', 'unknown')
        description = data.get('description', '')
        symptoms = data.get('symptoms', [])
        expected_mttr = data.get('expected_mttr_minutes', 5.0)
        user_impact = data.get('user_impact', 'DEGRADED')
        severity = data.get('sev', 'P2')
        
        # Parse recovery steps
        recovery_steps = []
        for i, step_text in enumerate(data.get('recovery_steps', []), 1):
            # Try to extract step number and text
            step_desc = step_text.strip()
            recovery_steps.append(RecoveryStep(
                step_number=i,
                description=step_desc
            ))
        
        return FailureMode(
            mode_id=mode_id,
            description=description,
            symptoms=symptoms,
            recovery_steps=recovery_steps,
            expected_mttr_minutes=expected_mttr,
            user_impact=user_impact,
            severity=severity
        )
    
    def get_plan(self, agent_name: str) -> Optional[AgentLifePlan]:
        """Get life-plan for specific agent"""
        return self.plans.get(agent_name)
    
    def get_failure_modes(self, agent_name: str) -> List[FailureMode]:
        """Get failure modes for specific agent"""
        return self.failure_mode_index.get(agent_name, [])
    
    def find_matching_failure_modes(self, agent_name: str, symptoms: List[str]) -> List[FailureMode]:
        """Find failure modes matching given symptoms"""
        matching = []
        modes = self.get_failure_modes(agent_name)
        
        for mode in modes:
            # Simple keyword matching
            mode_symptoms_lower = [s.lower() for s in mode.symptoms]
            symptoms_lower = [s.lower() for s in symptoms]
            
            matches = sum(
                1 for symptom in symptoms_lower
                for mode_symptom in mode_symptoms_lower
                if symptom in mode_symptom or mode_symptom in symptom
            )
            
            if matches > 0:
                matching.append(mode)
        
        # Sort by severity
        severity_order = {"P1": 0, "P2": 1, "P3": 2}
        matching.sort(key=lambda m: severity_order.get(m.severity, 999))
        
        return matching
    
    def get_slos(self, agent_name: str) -> Dict[str, Any]:
        """Get SLOs for agent"""
        plan = self.get_plan(agent_name)
        return plan.performance_slos if plan else {}
    
    def get_playbook(self, agent_name: str, playbook_name: str) -> Optional[Dict[str, Any]]:
        """Get specific on-call playbook"""
        plan = self.get_plan(agent_name)
        if not plan:
            return None
        return plan.on_call_playbook.get(playbook_name)
    
    def get_all_metrics(self) -> List[Dict[str, str]]:
        """Get all metrics to monitor from all life-plans"""
        all_metrics = []
        for plan in self.plans.values():
            all_metrics.extend(plan.metrics_to_monitor)
        return all_metrics
