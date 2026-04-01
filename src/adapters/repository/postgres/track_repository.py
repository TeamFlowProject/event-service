import psycopg_pool
import uuid

from src.models.track import Track, Role
from src.adapters.repository.postgres.queries import (
    CREATE_TASK_QUERY,
    CREATE_ROLES_QUERY,
    UPSERT_ROLES_QUERY,
    DELETE_STALE_ROLES_QUERY,
    UPDATE_TRACKS_QUERY,
    DELETE_TRACKS_QUERY,
    DELETE_ROLES_QUERY,
    SELECT_TRACKS_QUERY,
    SELECT_ROLES_QUERY,
    SELECT_TRACKS_BY_EVENT_ID_QUERY,
    SELECT_ROLES_BY_EVENT_ID_QUERY,
)
from src.adapters.repository.errors import TrackNotFoundError


class TrackPostgresRepository:
    def __init__(self, pool: psycopg_pool.AsyncConnectionPool) -> None:
        self._pool = pool

    async def create_track(self, track: Track):
        """
        Create a new track

        Args:
            track (Track): The track to create
        """

        async with self._pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        CREATE_TASK_QUERY,
                        track.__dict__,
                    )

                    await cursor.executemany(
                        CREATE_ROLES_QUERY,
                        [role.__dict__ for role in track.required_roles],
                    )

    async def update_track(self, track: Track):
        """
        Update an existing track

        Args:
            track (Track): The track to update
        """

        role_dicts = [
            {**role.__dict__, "track_id": str(track.id)}
            for role in track.required_roles
        ]
        role_ids = [str(role.id) for role in track.required_roles]

        async with self._pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor() as cursor:
                    if role_dicts:
                        await cursor.executemany(UPSERT_ROLES_QUERY, role_dicts)

                    await cursor.execute(
                        DELETE_STALE_ROLES_QUERY,
                        {"track_id": str(track.id), "ids": role_ids},
                    )

                    await cursor.execute(
                        UPDATE_TRACKS_QUERY,
                        track.__dict__,
                    )

    async def delete_track(self, id: uuid.UUID):
        """
        Delete an existing track

        Args:
            id (uuid.UUID): The id of the track to delete
        """

        async with self._pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        DELETE_ROLES_QUERY,
                        {"track_id": str(id)},
                    )

                    await cursor.execute(
                        DELETE_TRACKS_QUERY,
                        {"id": str(id)},
                    )

    async def get_track(self, id: uuid.UUID) -> Track:
        """
        Get a track by id

        Args:
            id (uuid.UUID): The id of the track to get

        Returns:
            Track: The track with the given id
        """

        async with self._pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    SELECT_TRACKS_QUERY,
                    {"id": str(id)},
                )
                row = await cursor.fetchone()
                if row is None:
                    raise TrackNotFoundError(f"Track with id {id} not found")

                await cursor.execute(
                    SELECT_ROLES_QUERY,
                    {"track_id": str(id)},
                )
                roles = [
                    Role(
                        id=role[0],
                        track_id=role[1],
                        name=role[2],
                        description=role[3],
                        count=role[4],
                    )
                    for role in await cursor.fetchall()
                ]

                return Track(
                    id=row[0],
                    event_id=row[1],
                    name=row[2],
                    description=row[3],
                    max_team_count=row[4],
                    max_participants_count=row[5],
                    min_team_size=row[6],
                    max_team_size=row[7],
                    requirements=row[8],
                    status=row[9],
                    registration_deadline=row[10],
                    required_roles=roles,
                )

    async def get_tracks_by_event_id(self, event_id: uuid.UUID) -> list[Track]:
        """
        Get all tracks for an event

        Args:
            event_id (uuid.UUID): The id of the event to get tracks for

        Returns:
            list[Track]: A list of tracks for the given event
        """

        async with self._pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    SELECT_TRACKS_BY_EVENT_ID_QUERY,
                    {"event_id": str(event_id)},
                )
                rows = await cursor.fetchall()

                await cursor.execute(
                    SELECT_ROLES_BY_EVENT_ID_QUERY,
                    {"event_id": str(event_id)},
                )
                roles_by_track: dict[str, list[Role]] = {}
                for role in await cursor.fetchall():
                    track_id_str = str(role[1])
                    roles_by_track.setdefault(track_id_str, []).append(
                        Role(
                            id=role[0],
                            track_id=role[1],
                            name=role[2],
                            description=role[3],
                            count=role[4],
                        )
                    )

                return [
                    Track(
                        id=row[0],
                        event_id=row[1],
                        name=row[2],
                        description=row[3],
                        max_team_count=row[4],
                        max_participants_count=row[5],
                        min_team_size=row[6],
                        max_team_size=row[7],
                        requirements=row[8],
                        status=row[9],
                        registration_deadline=row[10],
                        required_roles=roles_by_track.get(str(row[0]), []),
                    )
                    for row in rows
                ]
