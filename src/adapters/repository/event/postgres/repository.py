from datetime import datetime, timezone
from typing import Optional
import uuid
import psycopg.rows
import psycopg_pool

from src.adapters.repository.errors import EventNotFoundError
from src.adapters.repository.event.postgres.models import EventRow, ParticipantRow
from src.adapters.repository.event.postgres.queries import (
    CREATE_EVENT_QUERY,
    UPDATE_EVENT_QUERY,
    DELETE_EVENT_QUERY,
    SELECT_EVENT_QUERY,
    CREATE_PARTICIPANT_QUERY,
    REGISTER_PARTICIPANT_QUERY,
    SELECT_EVENTS_QUERY_BY_ID,
    SELECT_EVENTS_QUERY_BY_NUM,
    SELECT_PARTICIPANTS_QUERY_BY_NUM,
    SELECT_PARTICIPANTS_QUERY_BY_ID,
)
from src.models import Event
from src.models.event import Participant


class EventPostgresRepository:
    def __init__(self, pool: psycopg_pool.AsyncConnectionPool) -> None:
        self._pool = pool

    async def create_event(self, event: Event) -> None:
        """
        Create a new event
        Args:
            event (Event): The event to create
        """

        async with self._pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    CREATE_EVENT_QUERY,
                    {
                        "id": str(event.id),
                        "name": event.name,
                        "description": event.description,
                        "type": event.type,
                        "registration_start": event.registration_start,
                        "registration_end": event.registration_end,
                        "holding_start": event.holding_start,
                        "holding_end": event.holding_end,
                        "created_at": event.created_at,
                        "organizers": event.organizers,
                        "rules": event.rules,
                        "faq": event.faq,
                        "status": event.status,
                    },
                )

    async def update_event(self, event: Event) -> None:
        """
        Update an existing event
        Args:
            event (Event): The event to update
        """

        async with self._pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    UPDATE_EVENT_QUERY,
                    {
                        "id": str(event.id),
                        "name": event.name,
                        "description": event.description,
                        "type": event.type,
                        "registration_start": event.registration_start,
                        "registration_end": event.registration_end,
                        "holding_start": event.holding_start,
                        "holding_end": event.holding_end,
                        "organizers": event.organizers,
                        "rules": event.rules,
                        "faq": event.faq,
                        "status": event.status,
                    },
                )
                row = await cursor.fetchone()
                if row is None:
                    raise EventNotFoundError(f"Event with id {event.id} not found")

    async def delete_event(self, event_id: uuid.UUID) -> None:
        """
        Delete an existing event
        Args:
            event_id (uuid.UUID): The event to delete
        """

        async with self._pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(DELETE_EVENT_QUERY, {"id": str(event_id)})
                row = await cursor.fetchone()
                if row is None:
                    raise EventNotFoundError(f"Event with id {event_id} not found")

    async def get_event_by_id(self, event_id: uuid.UUID) -> Event:
        """
        Get a event by id

        Args:
            event_id (uuid.UUID): The id of the event to get

        Returns:
            Event: The event with the given id
        """
        async with self._pool.connection() as conn:
            async with conn.cursor(
                row_factory=psycopg.rows.class_row(EventRow)
            ) as cursor:
                await cursor.execute(SELECT_EVENT_QUERY, {"id": str(event_id)})
                row = await cursor.fetchone()
                if row is None:
                    raise EventNotFoundError(f"Event with id {event_id} not found")

                return row.to_model()

    async def get_events_page_by_id(
        self, event_id: uuid.UUID, limit: int
    ) -> tuple[list[Event], Optional[uuid.UUID]]:
        """
        Get events page by id
        Args:
            event_id (uuid.UUID): The id of the event to get
            limit (int): The number of events to get
        Returns:
            tuple[list[Event], Optional[uuid.UUID]]: The events page and cursor
        """
        async with self._pool.connection() as conn:
            async with conn.cursor(
                row_factory=psycopg.rows.class_row(EventRow)
            ) as cursor:
                await cursor.execute(
                    SELECT_EVENTS_QUERY_BY_ID, {"id": str(event_id), "limit": limit}
                )
                rows = await cursor.fetchall()

                if not rows:
                    return [], None

                return (
                    [row.to_model() for row in rows],
                    rows[-1].id,
                )

    async def get_events_page_by_num(
        self, offset: int, limit: int
    ) -> tuple[list[Event], Optional[uuid.UUID]]:
        """
        Get events page by num
        Args:
            offset (int): The offset of the page
            limit (int): The number of events to get
        Returns:
            tuple[list[Event], Optional[uuid.UUID]]: The events page and cursor
        """
        async with self._pool.connection() as conn:
            async with conn.cursor(
                row_factory=psycopg.rows.class_row(EventRow)
            ) as cursor:
                await cursor.execute(
                    SELECT_EVENTS_QUERY_BY_NUM, {"offset": offset, "limit": limit}
                )
                rows = await cursor.fetchall()

                if not rows:
                    return [], None

                return (
                    [row.to_model() for row in rows],
                    rows[-1].id,
                )

    async def add_participant(
        self, event_id: uuid.UUID, participant: Participant
    ) -> None:
        """
        Add a participant to an event
        Args:
            event_id (uuid.UUID): The id of the event to add
            participant (Participant): The participant to add
        Returns:
            None
        """
        async with self._pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        CREATE_PARTICIPANT_QUERY,
                        {
                            "id": str(participant.id),
                            "name": participant.name,
                            "surname": participant.surname,
                            "patronymic": participant.patronymic,
                        },
                    )
                    await cursor.execute(
                        REGISTER_PARTICIPANT_QUERY,
                        {
                            "event_id": str(event_id),
                            "participant_id": str(participant.id),
                            "have_team": participant.have_team,
                            "registered_at": datetime.now(tz=timezone.utc),
                        },
                    )

    async def get_participants_by_id(
        self, event_id: uuid.UUID, participant_id: uuid.UUID, limit: int
    ) -> tuple[list[Participant], Optional[uuid.UUID]]:
        """
        Get participant page by id
        Args:
            event_id (uuid.UUID): The id of the event from get participants
            participant_id (uuid.UUID): The id of the participant to get
            limit (int): The number of participants to get
        Returns:
            tuple[list[Participant], Optional[uuid.UUID]]: The participant page and cursor
        """
        async with self._pool.connection() as conn:
            async with conn.cursor(
                row_factory=psycopg.rows.class_row(ParticipantRow)
            ) as cursor:
                await cursor.execute(
                    SELECT_PARTICIPANTS_QUERY_BY_ID,
                    {
                        "event_id": str(event_id),
                        "participant_id": str(participant_id),
                        "limit": limit,
                    },
                )
                rows = await cursor.fetchall()

                if not rows:
                    return [], None

                return (
                    [row.to_model(event_id) for row in rows],
                    rows[-1].id,
                )

    async def get_participants_by_num(
        self, event_id: uuid.UUID, offset: int, limit: int
    ) -> tuple[list[Participant], Optional[uuid.UUID]]:
        """
        Get participants page by num
        Args:
            event_id (uuid.UUID): The id of the event from get participants
            offset (int): The offset of the page
            limit (int): The number of participants to get
        Returns:
            tuple[list[Participant], Optional[uuid.UUID]]: The participants page and cursor
        """
        async with self._pool.connection() as conn:
            async with conn.cursor(
                row_factory=psycopg.rows.class_row(ParticipantRow)
            ) as cursor:
                await cursor.execute(
                    SELECT_PARTICIPANTS_QUERY_BY_NUM,
                    {"event_id": str(event_id), "offset": offset, "limit": limit},
                )
                rows = await cursor.fetchall()

                if not rows:
                    return [], None

                return (
                    [row.to_model(event_id) for row in rows],
                    rows[-1].id,
                )
