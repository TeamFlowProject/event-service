import psycopg

from src.models.event import Event


class EventPostgresRepository:
    def __init__(self, connection: psycopg.AsyncConnection) -> None: ...
