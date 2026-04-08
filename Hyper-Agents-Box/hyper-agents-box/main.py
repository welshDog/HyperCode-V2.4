from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram
import asyncio
import aiohttp
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
import os

app = FastAPI()

# Instrumentator
Instrumentator().instrument(app).expose(app)

@app.get("/health")
def health_check_root():
    return {"status": "healthy"}

@app.get("/agents/health")
def health_check():
    return {"status": "agents_healthy"}

# Metrics
VALIDATION_LATENCY = Histogram("agent_roundtrip_latency_seconds", "Coder roundtrip latency", ("result",))
VALIDATION_COUNT = Counter("agent_roundtrip_total", "Coder roundtrip count", ("result",))

# Tracing
resource = Resource(attributes={"service.name": "hyper-agents-box"})
trace.set_tracer_provider(TracerProvider(resource=resource))
otlp_exporter = OTLPSpanExporter(endpoint=os.getenv("OTLP_ENDPOINT", "http://jaeger:4317"), insecure=True)
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))
tracer = trace.get_tracer(__name__)

@app.on_event("startup")
async def start_worker():
    asyncio.create_task(run_validation_worker())

async def run_validation_worker():
    core = os.getenv("CORE_URL", "http://hypercode-core:8000")
    agents_url = f"{core}/agents"
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{agents_url}/") as resp:
                    agents = await resp.json()
                coder = next((a for a in agents if a.get("name") == "Coder"), None)
                if not coder:
                    await asyncio.sleep(5)
                    continue
                agent_id = coder["id"]
                payload = {"prompt": "return 'ok'"}
                with tracer.start_as_current_span("roundtrip"):
                    t0 = asyncio.get_event_loop().time()
                    async with session.post(f"{agents_url}/{agent_id}/send", json=payload) as sresp:
                        ok = sresp.status == 202
                    dt = asyncio.get_event_loop().time() - t0
                    VALIDATION_LATENCY.labels("success" if ok else "error").observe(dt)
                    VALIDATION_COUNT.labels("success" if ok else "error").inc()
        except Exception:
            VALIDATION_COUNT.labels("error").inc()
        await asyncio.sleep(30)
