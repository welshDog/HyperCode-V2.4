from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from app.core.config import settings
import logging
import os

def setup_telemetry(app):
    """
    Configure OpenTelemetry for the FastAPI application.
    """
    if os.getenv("OTEL_SDK_DISABLED", "").strip().lower() == "true":
        logging.info("OpenTelemetry SDK is disabled.")
        return

    if settings.OTLP_EXPORTER_DISABLED:
        logging.info("OpenTelemetry exporter is disabled.")
        return

    resource = Resource.create(attributes={
        "service.name": settings.SERVICE_NAME,
        "service.version": settings.VERSION,
        "deployment.environment": settings.ENVIRONMENT,
    })

    # Set up Tracer Provider
    tracer_provider = TracerProvider(resource=resource)
    
    # OTLP Exporter (sends traces to Jaeger/Tempo)
    otlp_exporter = OTLPSpanExporter(endpoint=settings.OTLP_ENDPOINT, insecure=True)
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)

    # Optional: Console Exporter for debugging in development
    if settings.ENVIRONMENT == "development":
        tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(tracer_provider)

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)

    # Instrument Logging
    LoggingInstrumentor().instrument(set_logging_format=True)
    
    # Instrument HTTP Client (httpx)
    HTTPXClientInstrumentor().instrument()

    # Instrument Database and Redis
    SQLAlchemyInstrumentor().instrument()
    RedisInstrumentor().instrument()
    
    logging.info(f"OpenTelemetry initialized for service: {settings.SERVICE_NAME}")
    return tracer_provider
