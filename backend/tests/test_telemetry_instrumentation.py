"""Regression coverage for app.core.telemetry (OpenTelemetry).

tests/conftest.py sets OTEL_SDK_DISABLED=true for the whole suite, so setup_telemetry() returns immediately in every
other test and an OpenTelemetry upgrade could break tracing without a single test failing. This file runs the real
setup in a fresh interpreter instead: tracing installs a process-wide TracerProvider that cannot be unset, and it must not
leak into the rest of the suite.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]

# Runs in a subprocess. Prints one JSON object of named boolean checks; every value must be true.
SCRIPT = r'''
import json, logging
from fastapi import FastAPI
from fastapi.testclient import TestClient
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from app.core import telemetry
from app.core.config import settings

records = []
class Capture(logging.Handler):
    def emit(self, record):
        records.append(record)

app = FastAPI()

@app.get("/ping")
async def ping():
    logging.getLogger("telemetry-test").warning("inside-request")
    return {"ok": True}

provider = telemetry.setup_telemetry(app)
exporter = InMemorySpanExporter()
provider.add_span_processor(SimpleSpanProcessor(exporter))
logging.getLogger("telemetry-test").addHandler(Capture())

response = TestClient(app).get("/ping")
spans = exporter.get_finished_spans()
server = [s for s in spans if s.kind.name == "SERVER"]
inside = [r for r in records if getattr(r, "msg", "") == "inside-request"]

checks = {
    "setup_returns_a_tracer_provider": isinstance(provider, TracerProvider),
    "provider_is_the_global_one": trace.get_tracer_provider() is provider,
    "request_succeeded": response.status_code == 200,
    "server_span_recorded": len(server) >= 1,
    "server_span_names_the_route": any("/ping" in s.name or "/ping" in str(dict(s.attributes)) for s in server),
    "resource_has_service_name": provider.resource.attributes.get("service.name") == settings.SERVICE_NAME,
    "log_records_carry_the_trace_id": bool(inside) and getattr(inside[0], "otelTraceID", "0") not in ("0", "", None),
    "httpx_instrumented": HTTPXClientInstrumentor().is_instrumented_by_opentelemetry,
    "sqlalchemy_instrumented": SQLAlchemyInstrumentor().is_instrumented_by_opentelemetry,
    "redis_instrumented": RedisInstrumentor().is_instrumented_by_opentelemetry,
    "logging_instrumented": LoggingInstrumentor().is_instrumented_by_opentelemetry,
}
print(json.dumps(checks))
'''


def test_setup_telemetry_instruments_a_real_request():
    env = {k: v for k, v in os.environ.items() if k != "OTEL_SDK_DISABLED"}
    env.update({
        "ENVIRONMENT": "test",
        "OTLP_EXPORTER_DISABLED": "false",
        # nothing listens here: the batch exporter fails in the background and logs, it never raises into a request
        "OTLP_ENDPOINT": "http://127.0.0.1:1",
        "PYTHONPATH": os.pathsep.join(p for p in (str(BACKEND_DIR), os.environ.get("PYTHONPATH")) if p),
    })
    proc = subprocess.run([sys.executable, "-c", SCRIPT], cwd=BACKEND_DIR, env=env, capture_output=True, text=True, timeout=180)
    assert proc.returncode == 0, f"telemetry subprocess failed:\n{proc.stderr[-3000:]}"
    checks = json.loads(proc.stdout.strip().splitlines()[-1])
    failed = sorted(name for name, ok in checks.items() if not ok)
    assert not failed, f"OpenTelemetry checks failed: {failed}\nall: {checks}"


def test_disabled_sdk_is_a_noop(monkeypatch):
    from fastapi import FastAPI

    from app.core.telemetry import setup_telemetry

    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    assert setup_telemetry(FastAPI()) is None
