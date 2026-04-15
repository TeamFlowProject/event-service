from typing import Optional
from src.service.event.protocols import EventRepository, KafkaProducer
from src.models.event import Event, Participant, EventStatusEnum
import src.adapters.repository.errors as adapter_errors
import src.service.errors as service_errors
import uuid


class EventService:
    def __init__(
        self,
        event_repository: EventRepository,
        kafka_producer: KafkaProducer,
    ) -> None:
        self._event_repository = event_repository
        self._kafka_producer = kafka_producer

    async def get_event_by_id(self, event_id: uuid.UUID) -> Event:
        """
        Get an event by ID

        Args:
            event_id (uuid.UUID): The ID of the event to get

        Returns:
            Event: The event with the given ID

        Raises:
            EventNotFoundError: If the event could not be found
        """
        try:
            return await self._event_repository.get_event_by_id(event_id)
        except adapter_errors.EventNotFoundError as e:
            raise service_errors.EventNotFoundError("Failed to get event") from e

    async def get_events_page(
        self,
        event_id: Optional[uuid.UUID] = None,
        offset: Optional[int] = None,
        limit: int = 10,
    ) -> tuple[list[Event], Optional[uuid.UUID]]:
        """
        Get events with pagination

        Supports two modes: get single event by ID or get list with offset pagination

        Args:
            event_id (Optional[uuid.UUID]): The ID of the event to get
            offset (Optional[int]): Number of events to skip
            limit (int): Maximum number of events to return

        Returns:
            tuple[list[Event], Optional[uuid.UUID]]: The events and cursor

        Raises:
            PaginationError: If both or neither of event_id and offset are specified
        """
        if (event_id is not None) and (offset is not None):
            raise service_errors.PaginationError(
                "Event id or offset must be specified"
            ) from None

        if event_id:
            return await self._event_repository.get_events_page_by_id(
                event_id=event_id, limit=limit
            )
        if offset is not None:
            return await self._event_repository.get_events_page_by_num(
                offset=offset, limit=limit
            )

        raise service_errors.PaginationError("Offset or id must be specified")

    async def create_event(self, event: Event) -> uuid.UUID:
        """
        Create a new event

        Args:
            event (Event): The event to create

        Returns:
            uuid.UUID: The ID of the created event

        Raises:
            EventCreationError: If the event could not be created
        """
        await self._event_repository.create_event(event)
        await self._kafka_producer.send_create_event(event)

        return event.id

    async def update_event(self, event: Event) -> None:
        """
        Update an existing event

        Updates full state of the event

        Args:
            event (Event): The event to update

        Raises:
            EventNotFoundError: If the event could not be updated
        """
        try:
            await self._event_repository.update_event(event)
            await self._kafka_producer.send_update_event(event)
        except adapter_errors.EventNotFoundError as e:
            raise service_errors.EventNotFoundError("Failed to update event") from e

    async def delete_event(self, event_id: uuid.UUID) -> None:
        """
        Delete an existing event

        Args:
            event_id (uuid.UUID): The ID of the event to delete

        Raises:
            EventNotFoundError: If the event could not be deleted
        """
        try:
            await self._event_repository.delete_event(event_id)
            await self._kafka_producer.send_delete_event(event_id)
        except adapter_errors.EventNotFoundError as e:
            raise service_errors.EventNotFoundError("Failed to delete event") from e

    async def add_participant(
        self, event_id: uuid.UUID, participant: Participant
    ) -> None:
        """
        Add a participant to an event

        Args:
            event_id (uuid.UUID): The ID of the event to add participant to
            participant (Participant): The participant to add

        Raises:
            EventNotFoundError: If the event could not be found
            ParticipantError: If the participant could not be added (event not OPEN)
        """
        event = await self.get_event_by_id(event_id)

        if event.status == EventStatusEnum.OPEN:
            await self._event_repository.add_participant(event_id, participant)
            await self._kafka_producer.send_participant(event, participant.id)
        else:
            raise service_errors.ParticipantError("Failed to add participant") from None

    async def get_participants(
        self,
        event_id: uuid.UUID,
        offset: Optional[int] = None,
        participant_id: Optional[uuid.UUID] = None,
        limit: int = 10,
    ) -> tuple[list[Participant], Optional[uuid.UUID]]:
        """
        Get participants for an event

        Supports two modes:
        - Get participant by ID (returns list with single participant)
        - Get list of participants with offset pagination

        Args:
            event_id (uuid.UUID): The ID of the event to get participants for
            offset (Optional[int]): Number of participants to skip (for pagination mode)
            participant_id (Optional[uuid.UUID]): The ID of the participant to get (for single lookup)
            limit (int): Maximum number of participants to return

        Returns:
            list[Participant]: List of participants (single item in ID mode, multiple in pagination mode)

        Raises:
            PaginationError: If both or neither of participant_id and offset are specified
            EventNotFoundError: If the event could not be found
            ParticipantNotFoundError: If the participant could not be found
        """
        if (participant_id is not None) and (offset is not None):
            raise service_errors.PaginationError(
                "Participant id or offset must be specified"
            ) from None

        try:
            if participant_id:
                return await self._event_repository.get_participants_by_id(
                    event_id, participant_id, limit
                )
            if offset is not None:
                return await self._event_repository.get_participants_by_num(
                    event_id, offset, limit
                )
            raise service_errors.PaginationError(
                "Participant id or offset must be specified"
            ) from None

        except adapter_errors.EventNotFoundError as e:
            raise service_errors.EventNotFoundError("Failed to get participant") from e
        except adapter_errors.ParticipantNotFoundError as e:
            raise service_errors.ParticipantNotFoundError(
                "Failed to get participant"
            ) from e
