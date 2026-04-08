"""ObserverAgent - System monitoring and pattern recognition for HyperCode.

ND-Friendly Design:
- Passive by default: watch without interrupting
- Clear alert thresholds with no surprise notifications
- Pattern recognition surfaces insights, never noise
- Everything observable: metrics, events, anomalies
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Set

from src.agents.hyper_agents.base_agent import (
    AgentArchetype,
    AgentStatus,
    HyperAgent,
    NDErrorResponse,
)


class AlertSeverity(Enum):
    """Alert levels - always explicit, never ambiguous."""

    INFO = "info"        # Informational, no action needed
    WARNING = "warning"  # Worth knowing, monitor closely
    CRITICAL = "critical"  # Needs attention now


class MetricType(Enum):
    """What kind of metric we're tracking."""

    COUNTER = "counter"    # Monotonically increasing value
    GAUGE = "gauge"        # Point-in-time value
    HISTOGRAM = "histogram"  # Distribution of values
    RATE = "rate"          # Events per second


@dataclass
class Metric:
    """A single observable measurement."""

    name: str
    value: float
    metric_type: MetricType = MetricType.GAUGE
    tags: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    unit: str = ""

    @property
    def label(self) -> str:
        tag_str = ",".join(f"{k}={v}" for k, v in self.tags.items())
        return f"{self.name}{{{tag_str}}}" if tag_str else self.name


@dataclass
class Alert:
    """A condition that crossed a threshold - always explains itself."""

    alert_id: str
    severity: AlertSeverity
    metric_name: str
    current_value: float
    threshold: float
    message: str
    what_to_do: str
    timestamp: float = field(default_factory=time.time)
    resolved: bool = False

    def resolve(self) -> None:
        """Mark alert as resolved with clear signal."""
        self.resolved = True

    @property
    def summary(self) -> str:
        status = "RESOLVED" if self.resolved else self.severity.value.upper()
        return f"[{status}] {self.metric_name}: {self.message}"


@dataclass
class AlertRule:
    """Define when to trigger an alert - explicit thresholds, no magic."""

    name: str
    metric_name: str
    threshold: float
    severity: AlertSeverity
    message_template: str
    what_to_do: str
    comparison: str = "gt"  # gt, lt, eq, gte, lte
    cooldown_seconds: float = 60.0
    _last_triggered: float = field(default=0.0, init=False, repr=False)

    def evaluate(self, value: float) -> bool:
        """Check if value crosses threshold."""
        ops = {
            "gt": value > self.threshold,
            "lt": value < self.threshold,
            "eq": value == self.threshold,
            "gte": value >= self.threshold,
            "lte": value <= self.threshold,
        }
        return ops.get(self.comparison, False)

    def is_cooled_down(self) -> bool:
        """Prevent alert spam - respect quiet time."""
        return (time.time() - self._last_triggered) >= self.cooldown_seconds


class ObserverAgent(HyperAgent):
    """ObserverAgent - Passive system monitoring with pattern recognition.

    The ObserverAgent watches silently and surfaces insights when they matter.
    It never shouts, never spams, and always explains what it found.

    Core Capabilities:
    - Real-time metric collection and aggregation
    - Threshold-based alerting with cooldown
    - Event stream with configurable window size
    - Pattern detection across metric history
    - Custom callback hooks for external systems

    ND-Friendly Features:
    - Silent by default: no noise unless thresholds are crossed
    - Every alert says WHAT happened AND what to do
    - Metrics window size is configurable (avoid data overwhelm)
    - Rate limiting on alerts (no notification floods)

    Example usage::

        observer = ObserverAgent(agent_id="sys-monitor-01")
        await observer.initialize()

        # Register a threshold alert
        observer.add_alert_rule(AlertRule(
            name="high-error-rate",
            metric_name="error_rate",
            threshold=0.05,
            severity=AlertSeverity.CRITICAL,
            message_template="Error rate at {value:.1%} (threshold: {threshold:.1%})",
            what_to_do="Check logs for root cause. Scale back traffic if needed.",
            comparison="gt",
        ))

        # Record a metric
        observer.record(Metric("error_rate", 0.08, MetricType.GAUGE))

        # Check for alerts
        alerts = observer.get_active_alerts()
    """

    ARCHETYPE = AgentArchetype.OBSERVER

    def __init__(
        self,
        name: str,
        archetype: AgentArchetype = AgentArchetype.OBSERVER,
        window_size: int = 100,
        alert_callback: Optional[Callable[[Alert], None]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(name=name, archetype=archetype, **kwargs)
        self.window_size = window_size
        self.alert_callback = alert_callback

        # Metric storage: name -> deque of (timestamp, value)
        self._metrics: Dict[str, Deque[tuple]] = defaultdict(
            lambda: deque(maxlen=window_size)
        )
        self._alert_rules: List[AlertRule] = []
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_history: List[Alert] = []
        self._event_log: Deque[Dict[str, Any]] = deque(maxlen=window_size)
        self._watchers: Set[str] = set()
        self._total_metrics_recorded: int = 0
        self._total_alerts_fired: int = 0

    async def initialize(self) -> None:
        """Start the observer - begins watching immediately."""
        self._log("ObserverAgent initializing...")
        self.status = AgentStatus.STARTING
        await asyncio.sleep(0)
        self.status = AgentStatus.READY
        self._log(
            f"ObserverAgent '{self.name}' watching. "
            f"Window: {self.window_size} samples. "
            f"Rules loaded: {len(self._alert_rules)}"
        )

    def record(self, metric: Metric) -> None:
        """Record a metric observation.

        Args:
            metric: The Metric to record.
        """
        self._metrics[metric.name].append((metric.timestamp, metric.value))
        self._total_metrics_recorded += 1
        self._log(
            f"Metric recorded: {metric.label} = {metric.value} "
            f"{metric.unit}".strip()
        )
        self._evaluate_rules(metric)

    def record_many(self, metrics: List[Metric]) -> None:
        """Batch record multiple metrics at once."""
        for metric in metrics:
            self.record(metric)

    def add_alert_rule(self, rule: AlertRule) -> None:
        """Register a new alerting rule.

        Args:
            rule: AlertRule defining the threshold and action.
        """
        self._alert_rules.append(rule)
        self._log(f"Alert rule added: '{rule.name}' on {rule.metric_name}")

    def _evaluate_rules(self, metric: Metric) -> None:
        """Check all rules against a newly recorded metric."""
        for rule in self._alert_rules:
            if rule.metric_name != metric.name:
                continue
            if not rule.evaluate(metric.value):
                # Resolve existing alert if condition cleared
                if rule.name in self._active_alerts:
                    self._active_alerts[rule.name].resolve()
                    self._log(f"Alert resolved: {rule.name}")
                continue
            if not rule.is_cooled_down():
                continue

            alert = Alert(
                alert_id=f"{rule.name}-{int(time.time())}",
                severity=rule.severity,
                metric_name=metric.name,
                current_value=metric.value,
                threshold=rule.threshold,
                message=rule.message_template.format(
                    value=metric.value,
                    threshold=rule.threshold,
                ),
                what_to_do=rule.what_to_do,
            )

            rule._last_triggered = time.time()
            self._active_alerts[rule.name] = alert
            self._alert_history.append(alert)
            self._total_alerts_fired += 1
            self._log(f"ALERT FIRED [{alert.severity.value.upper()}]: {alert.summary}")

            if self.alert_callback:
                self.alert_callback(alert)

    def get_metric_stats(self, metric_name: str) -> Dict[str, float]:
        """Get statistical summary for a metric.

        Returns dict with min, max, avg, latest, count.
        Returns empty dict if metric not found.
        """
        samples = list(self._metrics.get(metric_name, []))
        if not samples:
            return {}

        values = [v for _, v in samples]
        return {
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "latest": values[-1],
            "count": float(len(values)),
        }

    def get_active_alerts(self) -> List[Alert]:
        """Return all currently active (unresolved) alerts."""
        return [
            a for a in self._active_alerts.values() if not a.resolved
        ]

    def get_rate(self, metric_name: str, window_seconds: float = 60.0) -> float:
        """Calculate the rate of change for a metric over a time window.

        Args:
            metric_name: Name of the metric.
            window_seconds: How far back to look.

        Returns:
            Rate of change per second, or 0.0 if insufficient data.
        """
        now = time.time()
        cutoff = now - window_seconds
        samples = [
            (ts, val)
            for ts, val in self._metrics.get(metric_name, [])
            if ts >= cutoff
        ]
        if len(samples) < 2:
            return 0.0

        time_delta = samples[-1][0] - samples[0][0]
        if time_delta == 0:
            return 0.0

        value_delta = samples[-1][1] - samples[0][1]
        return value_delta / time_delta

    def log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Record a structured event to the event log."""
        event = {
            "event_type": event_type,
            "timestamp": time.time(),
            **data,
        }
        self._event_log.append(event)
        self._log(f"Event: {event_type} - {data}")

    @property
    def stats(self) -> Dict[str, Any]:
        """Current observer statistics."""
        return {
            "name": self.name,
            "status": self.status.value,
            "metrics_tracked": len(self._metrics),
            "total_recorded": self._total_metrics_recorded,
            "alert_rules": len(self._alert_rules),
            "active_alerts": len(self.get_active_alerts()),
            "total_alerts_fired": self._total_alerts_fired,
            "event_log_size": len(self._event_log),
        }

    def _log(self, message: str) -> None:
        print(f"[ObserverAgent:{self.name}] {message}")

    def shutdown(self) -> None:
        """Graceful shutdown - flush logs, clear watchers."""
        self._log("Initiating graceful shutdown...")
        super().shutdown()
        self._log(f"Shutdown complete. Final stats: {self.stats}")
