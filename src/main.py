import asyncio
import sys

import psycopg
import typer
import uvicorn
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from fastapi import FastAPI
from loguru import logger

from src.adapters.clients.kafka_producer import KafkaProducerClient
from src.adapters.repository.postgres.event_repository import EventPostgresRepository
from src.adapters.repository.postgres.track_repository import TrackPostgresRepository
from src.config import Settings
from src.controller.http.event_router import create_event_router
from src.controller.http.track_router import create_track_router
from src.controller.kafka.event_consumer import EventKafkaConsumer
from src.service.event_service import EventService
from src.service.track_service import TrackService


async def _run(settings: Settings) -> None:
    logger.debug("Connecting to database: {}", settings.database_dsn)
    db_connection = await psycopg.AsyncConnection.connect(settings.database_dsn)
    event_repository = EventPostgresRepository(db_connection)
    track_repository = TrackPostgresRepository(db_connection)
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


app = typer.Typer()


def _setup_logger(settings: Settings) -> None:
    logger.remove()
    logger.add(
        sink=sys.stderr,
        level=settings.log_level.upper(),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level:<8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - {message}",
    )


@app.command()
def run() -> None:
    settings = Settings()
    _setup_logger(settings)
    logger.debug("Settings loaded: {}", settings.model_dump())
    asyncio.run(_run(settings))


if __name__ == "__main__":
    app()
