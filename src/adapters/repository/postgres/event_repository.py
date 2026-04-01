import psycopg_pool

from src.models.event import Event


class EventPostgresRepository:
    def __init__(self, pool: psycopg_pool.AsyncConnectionPool) -> None:
        self._pool = pool
