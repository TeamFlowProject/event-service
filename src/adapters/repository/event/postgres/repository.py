from datetime import datetime
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
            async with conn.transaction():
                async with conn.cursor() as cursor:
                    await cursor.execute(CREATE_EVENT_QUERY, event.__dict__)

    async def update_event(self, event: Event) -> None:
        """
        Update an existing event
        Args:
            event (Event): The event to update
        """

        async with self._pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor() as cursor:
                    await cursor.execute(UPDATE_EVENT_QUERY, event.__dict__)

    async def delete_event(self, event_id: uuid.UUID) -> None:
        """
        Delete an existing event
        Args:
            event_id (uuid.UUID): The event to delete
        """

        async with self._pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor() as cursor:
                    await cursor.execute(DELETE_EVENT_QUERY, {"id": str(event_id)})

    async def get_event_by_id(self, event_id: uuid.UUID) -> Event:
        """
        Get a event by id

        Args:
            event_id (uuid.UUID): The id of the event to get

        Returns:
            Event: The event with the given id
        """
        async with self._pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor(
                    row_factory=psycopg.rows.class_row(EventRow)
                ) as cursor:
                    await cursor.execute(SELECT_EVENT_QUERY, {"id": str(event_id)})
                    row = await cursor.fetchone()
                    if row is None:
                        raise EventNotFoundError(f"Event with id {event_id} not found")

                    return Event(
                        id=row.id,
                        name=row.name,
                        description=row.description,
                        type=row.type,
                        registration_start=row.registration_start,
                        registration_end=row.registration_end,
                        holding_start=row.holding_start,
                        holding_end=row.holding_end,
                        created_at=row.created_at,
                        organizers=row.organizers,
                        rules=row.rules,
                        FAQ=row.FAQ,
                        status=row.status,
                    )

    async def get_events_page_by_id(
        self, event_id: uuid.UUID, limit: int
    ) -> list[Event]:
        """
        Get events page by id
        Args:
            event_id (uuid.UUID): The id of the event to get
        Returns:
            list[Event]: The events page
        """
        async with self._pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor(
                    row_factory=psycopg.rows.class_row(EventRow)
                ) as cursor:
                    await cursor.execute(
                        SELECT_EVENTS_QUERY_BY_ID, {"id": str(event_id), "limit": limit}
                    )
                    rows = await cursor.fetchall()

                    return [
                        Event(
                            id=row.id,
                            name=row.name,
                            description=row.description,
                            type=row.type,
                            registration_start=row.registration_start,
                            registration_end=row.registration_end,
                            holding_start=row.holding_start,
                            holding_end=row.holding_end,
                            created_at=row.created_at,
                            organizers=row.organizers,
                            rules=row.rules,
                            FAQ=row.FAQ,
                            status=row.status,
                        )
                        for row in rows
                    ]

    async def get_events_page_by_num(self, offset: int, limit: int) -> list[Event]:
        """
        Get events page by num
        Args:
            offset (int): The offset of the page
            limit (int): The number of events to get
        Returns:
            list[Event]: The events page
        """
        async with self._pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor(
                    row_factory=psycopg.rows.class_row(EventRow)
                ) as cursor:
                    await cursor.execute(
                        SELECT_EVENTS_QUERY_BY_NUM, {"offset": offset, "limit": limit}
                    )
                    rows = await cursor.fetchall()

                    return [
                        Event(
                            id=row.id,
                            name=row.name,
                            description=row.description,
                            type=row.type,
                            registration_start=row.registration_start,
                            registration_end=row.registration_end,
                            holding_start=row.holding_start,
                            holding_end=row.holding_end,
                            created_at=row.created_at,
                            organizers=row.organizers,
                            rules=row.rules,
                            FAQ=row.FAQ,
                            status=row.status,
                        )
                        for row in rows
                    ]

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
                    await cursor.execute(CREATE_PARTICIPANT_QUERY, participant.__dict__)
                    await cursor.execute(
                        REGISTER_PARTICIPANT_QUERY,
                        {
                            "id": uuid.uuid4(),
                            "event_id": str(event_id),
                            "participant_id": str(participant.id),
                            "have_team": False,
                            "registered_at": datetime.now(),
                        },
                    )

    async def get_participants_by_id(
        self, event_id: uuid.UUID, participant_id: uuid.UUID, limit: int
    ) -> list[Participant]:
        """
        Get participant page by id
        Args:
            event_id (uuid.UUID): The id of the event from get participants
            participant_id (uuid.UUID): The id of the participant to get
            limit (int): The number of participants to get
        Returns:
            list[Participant]: The participant page
        """
        async with self._pool.connection() as conn:
            async with conn.transaction():
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

                    return [
                        Participant(
                            id=row.id,
                            event_id=event_id,
                            name=row.name,
                            surname=row.surname,
                            patronymic=row.patronymic,
                            have_team=False,
                        )
                        for row in rows
                    ]

    async def get_participants_by_num(
        self, event_id: uuid.UUID, offset: int, limit: int
    ) -> list[Participant]:
        """
        Get participants page by num
        Args:
            event_id (uuid.UUID): The id of the event from get participants
            offset (int): The offset of the page
            limit (int): The number of participants to get
        Returns:
            list[Participant]: The participants page
        """
        async with self._pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor(
                    row_factory=psycopg.rows.class_row(ParticipantRow)
                ) as cursor:
                    await cursor.execute(
                        SELECT_PARTICIPANTS_QUERY_BY_NUM,
                        {"event_id": str(event_id), "offset": offset, "limit": limit},
                    )
                    rows = await cursor.fetchall()

                    return [
                        Participant(
                            id=row.id,
                            event_id=event_id,
                            name=row.name,
                            surname=row.surname,
                            patronymic=row.patronymic,
                            have_team=False,
                        )
                        for row in rows
                    ]
