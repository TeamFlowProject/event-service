import asyncio
import psycopg_pool
import uvicorn
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from fastapi import FastAPI
from loguru import logger

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from src.core.tracing import setup_tracing
from src.core.metrics import metrics_endpoint
from src.adapters.clients.kafka_producer import KafkaProducerClient, dto_serializer
from src.adapters.repository.event.postgres.repository import EventPostgresRepository
from src.adapters.repository.invitation.postgres.repository import (
    InvitationPostgresRepository,
)
from src.adapters.repository.track.postgres.repository import TrackPostgresRepository
from src.config import Settings
from src.controller.middleware import ObservabilityMiddleware
from src.controller.http.event.router import create_event_router
from src.controller.http.invitation.router import create_invitation_router
from src.controller.http.track.router import create_track_router
from src.controller.kafka.event_consumer import EventKafkaConsumer
from src.service.event.service import EventService
from src.service.invitation.service import InvitationService
from src.service.track.service import TrackService


async def run_application(settings: Settings) -> None:
    if settings.otel_enabled:
        setup_tracing(
            service_name=settings.otel_service_name,
            otlp_endpoint=settings.otel_exporter_otlp_endpoint,
        )
        logger.debug(
            "Tracing initialized: service={}, endpoint={}",
            settings.otel_service_name,
            settings.otel_exporter_otlp_endpoint,
        )
    else:
        logger.warning("Tracing is DISABLED (OTEL_ENABLED=false)")

    logger.debug("Connecting to database: {}", settings.database_dsn)
    db_connection = psycopg_pool.AsyncConnectionPool(
        settings.database_dsn,
        min_size=settings.database_min_connections,
        max_size=settings.database_max_connections,
    )
    event_repository = EventPostgresRepository(db_connection)  # type: ignore
    track_repository = TrackPostgresRepository(db_connection)  # type: ignore
    invitation_repository = InvitationPostgresRepository(db_connection)  # type: ignore
    logger.debug("Database connection established")

    logger.debug("Starting Kafka producer: {}", settings.kafka_bootstrap)
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap,
        value_serializer=dto_serializer,
    )
    await producer.start()
    kafka_producer = KafkaProducerClient(producer)
    logger.debug("Kafka producer started")

    event_service = EventService(event_repository, kafka_producer)
    track_service = TrackService(track_repository, kafka_producer)
    invitation_service = InvitationService(invitation_repository, kafka_producer)
    logger.debug("EventService initialized")

    fastapi_app = FastAPI(title="Event Service")
    event_router = create_event_router(event_service)
    track_router = create_track_router(track_service)
    invitation_router = create_invitation_router(invitation_service)
    fastapi_app.include_router(event_router)
    fastapi_app.include_router(track_router)
    fastapi_app.include_router(invitation_router)
    logger.debug("HTTP router registered")

    if settings.otel_enabled:
        FastAPIInstrumentor.instrument_app(
            fastapi_app,
            excluded_urls="metrics,health,readiness",
        )
        logger.debug("OpenTelemetry instrumentation applied")

    fastapi_app.add_middleware(ObservabilityMiddleware)
    logger.debug("Observability middleware added")

    fastapi_app.add_route("/metrics", metrics_endpoint)
    logger.debug("Metrics endpoint registered at /metrics")

    consumer = AIOKafkaConsumer(
        settings.kafka_topic_commands,
        bootstrap_servers=settings.kafka_bootstrap,
        group_id=settings.kafka_group_id,
    )
    kafka_consumer = EventKafkaConsumer(consumer, event_service)
    logger.debug(
        "Kafka consumer created: topic={}, group={}",
        settings.kafka_topic_commands,
        settings.kafka_group_id,
    )

    config = uvicorn.Config(
        fastapi_app, host=settings.http_host, port=settings.http_port
    )
    server = uvicorn.Server(config)
    logger.info("Starting service on {}:{}", settings.http_host, settings.http_port)

    try:
        await asyncio.gather(
            server.serve(),
            kafka_consumer.start(),
        )
    finally:
        logger.debug("Shutting down")
        await consumer.stop()
        await producer.stop()
        await db_connection.close()
        logger.info("Shutdown complete")
