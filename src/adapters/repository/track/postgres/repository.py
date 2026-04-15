import uuid

import psycopg.rows
from psycopg.errors import ForeignKeyViolation
import psycopg_pool

from src.models.track import Track, Role, TrackStatusEnum
from src.adapters.repository.track.postgres.queries import (
    CREATE_TRACK_QUERY,
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
from src.adapters.repository.errors import TrackNotFoundError, EventNotFoundError
from .models import TrackRow, RoleRow


class TrackPostgresRepository:
    def __init__(self, pool: psycopg_pool.AsyncConnectionPool) -> None:
        self._pool = pool

    async def create_track(self, track: Track):
        """
        Create a new track

        Args:
            track (Track): The track to create

        Raises:
            EventNotFoundError: If the referenced event does not exist
        """

        try:
            async with self._pool.connection() as conn:
                async with conn.transaction():
                    async with conn.cursor() as cursor:
                        await cursor.execute(
                            CREATE_TRACK_QUERY,
                            track.__dict__,
                        )

                        if track.required_roles:
                            await cursor.executemany(
                                CREATE_ROLES_QUERY,
                                [role.__dict__ for role in track.required_roles],
                            )
        except ForeignKeyViolation:
            raise EventNotFoundError(f"Event with id {track.event_id} not found")

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
                    await cursor.execute(
                        UPDATE_TRACKS_QUERY,
                        track.__dict__,
                    )
                    if await cursor.fetchone() is None:
                        raise TrackNotFoundError(f"Track with id {track.id} not found")

                    if role_dicts:
                        await cursor.executemany(UPSERT_ROLES_QUERY, role_dicts)

                    await cursor.execute(
                        DELETE_STALE_ROLES_QUERY,
                        {"track_id": str(track.id), "ids": role_ids},
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
                    if await cursor.fetchone() is None:
                        raise TrackNotFoundError(f"Track with id {id} not found")

    async def get_track(self, id: uuid.UUID) -> Track:
        """
        Get a track by id

        Args:
            id (uuid.UUID): The id of the track to get

        Returns:
            Track: The track with the given id
        """

        async with self._pool.connection() as conn:
            async with conn.cursor(
                row_factory=psycopg.rows.class_row(TrackRow)
            ) as track_cursor:
                await track_cursor.execute(SELECT_TRACKS_QUERY, {"id": str(id)})
                row = await track_cursor.fetchone()
                if row is None:
                    raise TrackNotFoundError(f"Track with id {id} not found")

            async with conn.cursor(
                row_factory=psycopg.rows.class_row(RoleRow)
            ) as role_cursor:
                await role_cursor.execute(SELECT_ROLES_QUERY, {"track_id": str(id)})
                roles = [
                    Role(
                        id=role.id,
                        track_id=role.track_id,
                        name=role.name,
                        description=role.description,
                        count=role.count,
                    )
                    for role in await role_cursor.fetchall()
                ]

                return Track(
                    id=row.id,
                    event_id=row.event_id,
                    name=row.name,
                    description=row.description,
                    max_team_count=row.max_team_count,
                    max_participants_count=row.max_participants_count,
                    min_team_size=row.min_team_size,
                    max_team_size=row.max_team_size,
                    requirements=row.requirements,
                    status=TrackStatusEnum(row.status),
                    registration_deadline=row.registration_deadline,
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
            async with conn.cursor(
                row_factory=psycopg.rows.class_row(TrackRow)
            ) as track_cursor:
                await track_cursor.execute(
                    SELECT_TRACKS_BY_EVENT_ID_QUERY,
                    {"event_id": str(event_id)},
                )
                rows = await track_cursor.fetchall()

            async with conn.cursor(
                row_factory=psycopg.rows.class_row(RoleRow)
            ) as role_cursor:
                await role_cursor.execute(
                    SELECT_ROLES_BY_EVENT_ID_QUERY,
                    {"event_id": str(event_id)},
                )
                roles_by_track: dict[uuid.UUID, list[Role]] = {}
                for role in await role_cursor.fetchall():
                    roles_by_track.setdefault(role.track_id, []).append(
                        Role(
                            id=role.id,
                            track_id=role.track_id,
                            name=role.name,
                            description=role.description,
                            count=role.count,
                        )
                    )

                return [
                    Track(
                        id=row.id,
                        event_id=row.event_id,
                        name=row.name,
                        description=row.description,
                        max_team_count=row.max_team_count,
                        max_participants_count=row.max_participants_count,
                        min_team_size=row.min_team_size,
                        max_team_size=row.max_team_size,
                        requirements=row.requirements,
                        status=TrackStatusEnum(row.status),
                        registration_deadline=row.registration_deadline,
                        required_roles=roles_by_track.get(row.id, []),
                    )
                    for row in rows
                ]
