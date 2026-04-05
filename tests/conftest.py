import pytest
import pytest_asyncio

import psycopg_pool
from testcontainers.postgres import PostgresContainer
from src.adapters.repository.track.postgres.repository import TrackPostgresRepository
from migrations.migrate import up


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
