import uuid

import psycopg_pool
import pytest
import pytest_asyncio
from aiokafka import AIOKafkaProducer
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from testcontainers.kafka import KafkaContainer
from testcontainers.postgres import PostgresContainer

from migrations.migrate import up
from src.adapters.clients.kafka_producer import KafkaProducerClient, dto_serializer
from src.adapters.repository.track.postgres.repository import TrackPostgresRepository
from src.controller.http.track.router import create_track_router
from src.service.track.service import TrackService


@pytest.fixture()
def postgres_container():
    with PostgresContainer("postgres:17") as pg:
        host = pg.get_container_host_ip()
        port = pg.get_exposed_port(5432)
        user = pg.username
        password = pg.password
        dbname = pg.dbname
        dsn = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        yoyo_dsn = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{dbname}"
        up(yoyo_dsn)
        yield dsn


@pytest_asyncio.fixture()
async def pool(postgres_container):
    async with psycopg_pool.AsyncConnectionPool(
        conninfo=postgres_container,
        min_size=1,
        max_size=2,
    ) as pool:
        yield pool


@pytest_asyncio.fixture()
async def track_repository(pool):
    return TrackPostgresRepository(pool)


@pytest.fixture(scope="module")
def kafka_container():
    with KafkaContainer() as kafka:
        yield kafka.get_bootstrap_server()


@pytest_asyncio.fixture
async def kafka_producer_client(kafka_container):
    producer = AIOKafkaProducer(
        bootstrap_servers=kafka_container,
        value_serializer=dto_serializer,
    )
    await producer.start()
    yield KafkaProducerClient(producer)
    await producer.stop()


@pytest_asyncio.fixture
async def track_service(track_repository, kafka_producer_client):
    return TrackService(track_repository, kafka_producer_client)


@pytest_asyncio.fixture
async def http_client(track_service):
    app = FastAPI()
    app.include_router(create_track_router(track_service))
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest_asyncio.fixture
async def event_id(pool):
    eid = uuid.uuid4()
    async with pool.connection() as conn:
        await conn.execute("INSERT INTO events (id) VALUES (%s)", (str(eid),))
    return eid
