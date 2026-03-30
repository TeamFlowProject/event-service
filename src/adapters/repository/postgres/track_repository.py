import psycopg

from src.models.track import Track


class TrackPostgresRepository:
    def __init__(self, connection: psycopg.AsyncConnection) -> None: ...
