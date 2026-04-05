import asyncio

import psycopg_pool
import uvicorn
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from fastapi import FastAPI
from loguru import logger

from src.adapters.clients.kafka_producer import KafkaProducerClient
from src.adapters.repository.event.postgres.repository import EventPostgresRepository
from src.adapters.repository.track.postgres.repository import TrackPostgresRepository
from src.config import Settings
from src.controller.http.event.router import create_event_router
from src.controller.http.track.router import create_track_router
from src.controller.kafka.event_consumer import EventKafkaConsumer
from src.service.event.service import EventService
from src.service.track.service import TrackService


async def run_application(settings: Settings) -> None:
    logger.debug("Connecting to database: {}", settings.database_dsn)
    db_connection = psycopg_pool.AsyncConnectionPool(
        settings.database_dsn,
        min_size=settings.database_min_connections,
        max_size=settings.database_max_connections,
    )
    event_repository = EventPostgresRepository(db_connection)  # type: ignore
    track_repository = TrackPostgresRepository(db_connection)  # type: ignore
    logger.debug("Database connection established")

    logger.debug("Starting Kafka producer: {}", settings.kafka_bootstrap)
    producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_bootstrap)
    await producer.start()
    kafka_producer = KafkaProducerClient(producer)
    logger.debug("Kafka producer started")

    event_service = EventService(event_repository, kafka_producer)
    track_service = TrackService(track_repository, kafka_producer)
    logger.debug("EventService initialized")

    fastapi_app = FastAPI(title="Event Service")
    event_router = create_event_router(event_service)
    track_router = create_track_router(track_service)
    fastapi_app.include_router(event_router)
    fastapi_app.include_router(track_router)
    logger.debug("HTTP router registered")

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
