"""Super Hyper BROski Agent - Full Featured FastAPI Service with Premium Features."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from collections import deque
from datetime import datetime
from typing import Any
from fastapi import FastAPI, Request, Response

sys.path.append(os.path.join(os.path.dirname(__file__), "../../backend"))
# No separate metrics module - metrics are defined inline below

from fastapi import FastAPI
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from pydantic import BaseModel

# ============================================================================
# ENHANCED JSON LOGGING
# ============================================================================


class JSONFormatter(logging.Formatter):
    """Format logs as JSON for Loki integration."""

    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "component": record.name,
            "message": record.getMessage(),
            "agent": "super-hyper-broski-agent",
        }
        # Add structured fields
        for attr in ["action", "tier", "ram_pct", "reason", "bro_mode", "vibe"]:
            if hasattr(record, attr):
                log_data[attr] = getattr(record, attr)
        return json.dumps(log_data)


logger = logging.getLogger("super-hyper-broski-agent")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
logger.propagate = False

# ============================================================================
# PROMETHEUS METRICS
# ============================================================================

PROM_REGISTRY = CollectorRegistry()

# Core metrics
BROSKI_REQUESTS_TOTAL = Counter(
    "broski_requests_total",
    "Total requests to BROski agent",
    ["endpoint", "method"],
    registry=PROM_REGISTRY,
)
BROSKI_VIBE_LEVEL = Gauge(
    "broski_vibe_level",
    "Current vibe level (0-100)",
    registry=PROM_REGISTRY,
)
BROSKI_ENERGY = Gauge(
    "broski_energy",
    "BROski energy level (0-100)",
    registry=PROM_REGISTRY,
)
BROSKI_COOLNESS = Gauge(
    "broski_coolness",
    "Coolness factor (0-100)",
    registry=PROM_REGISTRY,
)
BROSKI_ACTIONS_TOTAL = Counter(
    "broski_actions_total",
    "BROski actions performed",
    ["action_type"],
    registry=PROM_REGISTRY,
)
BROSKI_RESPONSE_TIME = Histogram(
    "broski_response_time_seconds",
    "Response time in seconds",
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 5],
    registry=PROM_REGISTRY,
)
BROSKI_CONNECTIONS = Gauge(
    "broski_active_connections",
    "Active connections",
    registry=PROM_REGISTRY,
)
BROSKI_PARTY_METER = Gauge(
    "broski_party_meter",
    "Party meter (0-100)",
    registry=PROM_REGISTRY,
)
BROSKI_UPTIME_SECONDS = Gauge(
    "broski_uptime_seconds",
    "Uptime in seconds",
    registry=PROM_REGISTRY,
)

# ============================================================================
# FASTAPI APP SETUP
# ============================================================================

app = FastAPI(
    title="Super Hyper BROski Agent",
    description="The most BROsome agent in the HyperCode ecosystem",
    version="1.0.0",
)

# ============================================================================
# STATE VARIABLES
# ============================================================================

START_TIME = time.time()
VIBE_HISTORY: deque = deque(maxlen=100)
ENERGY_LEVEL = 100
ACTIVE_CONNECTIONS = 0
PARTY_MODE = False
COOLNESS_FACTOR = 100

# ============================================================================
# MODELS
# ============================================================================


class BROski_Status(BaseModel):
    status: str
    vibe: int
    energy: int
    coolness: int
    uptime_seconds: float
    message: str


class BROski_Action(BaseModel):
    action: str
    intensity: int
    description: str
    result: str


class BROski_Party_Mode(BaseModel):
    enabled: bool
    party_level: int
    vibes: int
    message: str


# ============================================================================
# MIDDLEWARE
# ============================================================================


@app.middleware("http")
async def track_connections(request: Request, call_next):
    global ACTIVE_CONNECTIONS
    ACTIVE_CONNECTIONS += 1
    BROSKI_CONNECTIONS.set(ACTIVE_CONNECTIONS)

    start = time.time()

    try:
        response = await call_next(request)
        duration = time.time() - start
        BROSKI_RESPONSE_TIME.observe(duration)
        BROSKI_REQUESTS_TOTAL.labels(
            endpoint=request.url.path, method=request.method
        ).inc()
        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={
                "action": "request",
                "method": request.method,
                "endpoint": request.url.path,
                "duration_ms": duration * 1000,
            },
        )
        return response
    finally:
        ACTIVE_CONNECTIONS -= 1
        BROSKI_CONNECTIONS.set(ACTIVE_CONNECTIONS)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def update_vibe(delta: int = 0) -> int:
    """Update and track vibe level."""
    global VIBE_HISTORY, ENERGY_LEVEL, COOLNESS_FACTOR

    current_vibe = 50 + (ENERGY_LEVEL // 2) + delta
    current_vibe = max(0, min(100, current_vibe))  # Clamp 0-100

    VIBE_HISTORY.append(current_vibe)
    BROSKI_VIBE_LEVEL.set(current_vibe)
    BROSKI_ENERGY.set(ENERGY_LEVEL)
    BROSKI_COOLNESS.set(COOLNESS_FACTOR)

    return current_vibe


def calculate_vibe_trend() -> str:
    """Calculate vibe trend."""
    if len(VIBE_HISTORY) < 2:
        return "stable"

    recent = list(VIBE_HISTORY)[-5:]
    avg = sum(recent) / len(recent)
    latest = recent[-1]

    if latest > avg + 5:
        return "📈 rising"
    elif latest < avg - 5:
        return "📉 dropping"
    else:
        return "➡️ stable"


def calculate_uptime() -> float:
    """Calculate uptime in seconds."""
    uptime = time.time() - START_TIME
    BROSKI_UPTIME_SECONDS.set(uptime)
    return uptime


# ============================================================================
# ENDPOINTS
# ============================================================================


@app.get("/")
async def root() -> dict[str, Any]:
    """Root endpoint - BROski intro."""
    vibe = update_vibe(5)

    logger.info(
        "Root endpoint accessed - ready to BRO!",
        extra={"action": "root", "vibe": vibe, "bro_mode": "ON"},
    )

    return {
        "agent": "Super Hyper BROski Agent",
        "version": "1.0.0",
        "status": "🤙 BROski Mode ACTIVE",
        "vibe": vibe,
        "message": "Yo, what's up BRO? Ready to get things DONE? 🔥",
        "endpoints": [
            "/health",
            "/status",
            "/metrics",
            "/capabilities",
            "/vibe-check",
            "/energy-boost",
            "/party-mode",
            "/broski-actions",
            "/coolness-factor",
            "/ultra-mode",
        ],
    }


@app.get("/health")
async def health() -> BROski_Status:
    """Health check with BROski flair."""
    uptime = calculate_uptime()
    vibe = update_vibe(10)

    logger.info(
        "Health check - system BROtastic",
        extra={"action": "health", "vibe": vibe, "uptime": uptime},
    )

    return BROski_Status(
        status="healthy",
        vibe=vibe,
        energy=ENERGY_LEVEL,
        coolness=COOLNESS_FACTOR,
        uptime_seconds=uptime,
        message="🤙 BROski Agent is PUMPED and ready to GO!",
    )


@app.get("/status")
async def status() -> dict[str, Any]:
    """Full status with all BROski metrics."""
    uptime = calculate_uptime()
    vibe = update_vibe()
    trend = calculate_vibe_trend()

    logger.info(
        "Status check", extra={"action": "status", "vibe": vibe, "energy": ENERGY_LEVEL}
    )

    return {
        "agent": "Super Hyper BROski Agent",
        "status": "🤙 OPERATIONAL",
        "metrics": {
            "vibe_level": vibe,
            "vibe_trend": trend,
            "energy": ENERGY_LEVEL,
            "coolness": COOLNESS_FACTOR,
            "active_connections": ACTIVE_CONNECTIONS,
            "party_mode": PARTY_MODE,
            "uptime_seconds": uptime,
            "uptime_formatted": f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s",
        },
        "capabilities": [
            "Energy boost",
            "Vibe check",
            "Party mode",
            "Coolness analysis",
            "BROski actions",
            "Ultra mode",
            "Metrics export",
        ],
    }


@app.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    BROSKI_ACTIONS_TOTAL.labels(action_type="metrics_request").inc()
    return Response(generate_latest(PROM_REGISTRY), media_type=CONTENT_TYPE_LATEST)


@app.get("/capabilities")
async def capabilities() -> dict[str, Any]:
    """Agent capabilities."""
    vibe = update_vibe()

    logger.info(
        "Capabilities requested", extra={"action": "capabilities", "vibe": vibe}
    )

    return {
        "name": "Super Hyper BROski Agent",
        "version": "1.0.0",
        "description": "The most BROsome agent in the HyperCode ecosystem",
        "capabilities": {
            "vibe_checking": {"enabled": True, "current_vibe": vibe, "max_vibe": 100},
            "energy_management": {
                "enabled": True,
                "current_energy": ENERGY_LEVEL,
                "max_energy": 100,
            },
            "party_mode": {
                "enabled": True,
                "status": "active" if PARTY_MODE else "standby",
            },
            "metrics_export": {"enabled": True, "format": "prometheus"},
            "coolness_analysis": {"enabled": True, "current_coolness": COOLNESS_FACTOR},
        },
        "endpoints": {
            "health": "Health check",
            "status": "Full status",
            "metrics": "Prometheus metrics",
            "vibe-check": "Check current vibe",
            "energy-boost": "Boost energy",
            "party-mode": "Enable party mode",
            "broski-actions": "Perform BROski action",
            "coolness-factor": "Get coolness",
            "ultra-mode": "ULTRA MODE!!!",
        },
    }


@app.get("/vibe-check")
async def vibe_check() -> dict[str, Any]:
    """Check current vibe."""
    vibe = update_vibe(15)
    trend = calculate_vibe_trend()

    logger.info(
        "Vibe check performed",
        extra={"action": "vibe_check", "vibe": vibe, "trend": trend},
    )

    return {
        "current_vibe": vibe,
        "trend": trend,
        "vibe_history": list(VIBE_HISTORY)[-10:],
        "energy_level": ENERGY_LEVEL,
        "party_mode": PARTY_MODE,
        "message": f"The vibes are {'IMMACULATE' if vibe > 80 else 'SOLID' if vibe > 60 else 'DECENT' if vibe > 40 else 'NEEDS WORK'}! 🤙",
    }


@app.post("/energy-boost")
async def energy_boost(amount: int = 10) -> dict[str, Any]:
    """Boost agent energy."""
    global ENERGY_LEVEL
    ENERGY_LEVEL = min(100, ENERGY_LEVEL + amount)
    vibe = update_vibe(20)

    BROSKI_ACTIONS_TOTAL.labels(action_type="energy_boost").inc()

    logger.info(
        f"Energy boosted by {amount}",
        extra={"action": "energy_boost", "amount": amount, "new_energy": ENERGY_LEVEL},
    )

    return BROski_Action(
        action="energy_boost",
        intensity=amount,
        description=f"Boosted energy by {amount}%",
        result=f"Energy now at {ENERGY_LEVEL}! Vibe is {vibe}! 🚀",
    )


@app.post("/party-mode")
async def toggle_party_mode(enable: bool = True) -> BROski_Party_Mode:
    """Toggle party mode."""
    global PARTY_MODE
    PARTY_MODE = enable
    vibe = update_vibe(30 if enable else -20)
    party_level = 100 if enable else 0

    BROSKI_ACTIONS_TOTAL.labels(action_type="party_mode_toggle").inc()
    BROSKI_PARTY_METER.set(party_level)

    logger.info(
        f"Party mode {'ENABLED' if enable else 'DISABLED'}",
        extra={"action": "party_mode", "enabled": enable, "party_level": party_level},
    )

    return BROski_Party_Mode(
        enabled=enable,
        party_level=party_level,
        vibes=vibe,
        message="🎉 PARTY TIME! 🎉" if enable else "⏸️ Party on pause...",
    )


@app.post("/broski-actions")
async def broski_actions(action_type: str = "celebrate") -> dict[str, Any]:
    """Perform BROski action."""
    global ENERGY_LEVEL, COOLNESS_FACTOR

    actions = {
        "celebrate": {
            "message": "🎉 CELEBRATING! 🎉",
            "energy_cost": 5,
            "coolness_gain": 10,
        },
        "code": {
            "message": "💻 CODING LIKE A BOSS! 💻",
            "energy_cost": 15,
            "coolness_gain": 20,
        },
        "debug": {
            "message": "🐛 CRUSHING BUGS! 🐛",
            "energy_cost": 20,
            "coolness_gain": 25,
        },
        "deploy": {
            "message": "🚀 LAUNCHING TO THE MOON! 🚀",
            "energy_cost": 30,
            "coolness_gain": 40,
        },
        "rest": {
            "message": "😴 RECHARGING BRO VIBES... 😴",
            "energy_cost": -20,
            "coolness_gain": 0,
        },
    }

    action_data = actions.get(action_type, actions["celebrate"])
    ENERGY_LEVEL = max(0, ENERGY_LEVEL - action_data["energy_cost"])
    COOLNESS_FACTOR = min(100, COOLNESS_FACTOR + action_data["coolness_gain"])

    vibe = update_vibe(action_data["coolness_gain"] // 2)

    BROSKI_ACTIONS_TOTAL.labels(action_type=action_type).inc()

    logger.info(
        f"BROski action: {action_type}",
        extra={
            "action": "broski_action",
            "type": action_type,
            "energy": ENERGY_LEVEL,
            "coolness": COOLNESS_FACTOR,
        },
    )

    return BROski_Action(
        action=action_type,
        intensity=action_data["coolness_gain"],
        description=action_data["message"],
        result=f"✅ {action_data['message']} | Energy: {ENERGY_LEVEL}% | Coolness: {COOLNESS_FACTOR}% | Vibe: {vibe}/100",
    )


@app.get("/coolness-factor")
async def coolness_factor() -> dict[str, Any]:
    """Get coolness analysis."""
    vibe = update_vibe()

    logger.info(
        "Coolness check",
        extra={"action": "coolness_check", "coolness": COOLNESS_FACTOR},
    )

    coolness_desc = (
        "🔥 ULTRA COOL 🔥"
        if COOLNESS_FACTOR > 80
        else (
            "😎 Pretty Cool"
            if COOLNESS_FACTOR > 60
            else "👍 Decent" if COOLNESS_FACTOR > 40 else "❄️ Chilling"
        )
    )

    return {
        "coolness_level": COOLNESS_FACTOR,
        "description": coolness_desc,
        "vibe": vibe,
        "energy": ENERGY_LEVEL,
        "party_mode": PARTY_MODE,
        "recommendations": [
            "Keep crushing it!" if COOLNESS_FACTOR > 70 else "Time to level up!",
            "Deploy something cool!" if COOLNESS_FACTOR < 50 else "You're on fire!",
            "The vibes are "
            + ("immaculate" if vibe > 80 else "solid" if vibe > 60 else "needs work"),
        ],
    }


@app.post("/ultra-mode")
async def ultra_mode() -> dict[str, Any]:
    """ACTIVATE ULTRA MODE!!"""
    global ENERGY_LEVEL, COOLNESS_FACTOR, PARTY_MODE

    ENERGY_LEVEL = 100
    COOLNESS_FACTOR = 100
    PARTY_MODE = True
    vibe = update_vibe(50)

    BROSKI_ACTIONS_TOTAL.labels(action_type="ultra_mode").inc()

    logger.info(
        "🔥 ULTRA MODE ACTIVATED 🔥",
        extra={"action": "ultra_mode", "energy": 100, "coolness": 100, "vibe": vibe},
    )

    return {
        "status": "🔥 ULTRA MODE ACTIVATED 🔥",
        "energy": ENERGY_LEVEL,
        "coolness": COOLNESS_FACTOR,
        "vibe": vibe,
        "party_mode": PARTY_MODE,
        "message": "🚀 YOU'VE UNLOCKED ULTRA MODE! 🚀",
        "effects": [
            "⚡ ENERGY MAXED",
            "❄️ COOLNESS MAXED",
            "🎉 PARTY MODE ON",
            "💥 VIBE THRUSTERS ENGAGED",
            "🤙 BRO STATUS: ULTIMATE",
        ],
    }


@app.on_event("startup")
async def startup():
    """Startup event."""
    logger.info("🤙 Super Hyper BROski Agent Starting Up! 🤙")
    update_vibe(50)


@app.on_event("shutdown")
async def shutdown():
    """Shutdown event."""
    logger.info("Powering down... See you next time, BRO!")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8015))
    logger.info(f"Starting Super Hyper BROski Agent on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
