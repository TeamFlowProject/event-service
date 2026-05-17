from typing import Optional
from loguru import logger
from opentelemetry import trace
import uuid

from src.service.tracing import trace_business_logic
from src.service.event.protocols import EventRepository, KafkaProducer
from src.models.event import Event, EventStatusEnum, Participant, ParticipantEvent
import src.adapters.repository.errors as adapter_errors
import src.service.errors as service_errors

tracer = trace.get_tracer(__name__)


class EventService:
    def __init__(
        self,
        event_repository: EventRepository,
        kafka_producer: KafkaProducer,
    ) -> None:
        self._event_repository = event_repository
        self._kafka_producer = kafka_producer

    @trace_business_logic("event_service")
    async def get_event_by_id(self, event_id: uuid.UUID) -> Event:
        span = trace.get_current_span()
        span.set_attribute("event.id", str(event_id))

        logger.info("service_receiving_event", event_id=str(event_id))

        try:
            event = await self._event_repository.get_event_by_id(event_id)
            logger.info("service_event_received", event_id=str(event_id))
            return event
        except adapter_errors.EventNotFoundError as e:
            raise service_errors.EventNotFoundError from e

    @trace_business_logic("event_service")
    async def get_events_page(
        self,
        event_id: Optional[uuid.UUID] = None,
        offset: Optional[int] = None,
        limit: int = 10,
    ) -> tuple[list[Event], Optional[uuid.UUID]]:
        span = trace.get_current_span()
        span.set_attribute("pagination.limit", limit)
        if event_id:
            span.set_attribute("pagination.cursor_id", str(event_id))
        if offset is not None:
            span.set_attribute("pagination.offset", offset)

        logger.info(
            "service_receiving_events_page",
            event_id=str(event_id) if event_id else None,
            offset=offset,
            limit=limit,
        )

        if (event_id is not None) and (offset is not None):
            raise service_errors.PaginationError(
                "Event id or offset must be specified"
            ) from None

        try:
            if event_id:
                return await self._event_repository.get_events_page_by_id(
                    event_id=event_id, limit=limit
                )
            if offset is not None:
                return await self._event_repository.get_events_page_by_num(
                    offset=offset, limit=limit
                )
        except adapter_errors.RepositoryError as e:
            raise service_errors.EventRepositoryError from e

        raise service_errors.PaginationError("Offset or id must be specified")

    @trace_business_logic("event_service")
    async def create_event(self, event: Event) -> uuid.UUID:
        span = trace.get_current_span()
        span.set_attribute("event.id", str(event.id))
        span.set_attribute("event.type", str(event.type))

        logger.info(
            "service_creating_event",
            event_id=str(event.id),
            event_type=str(event.type),
        )

        try:
            await self._event_repository.create_event(event)
            await self._kafka_producer.send_create_event(event)
            logger.info("service_event_created", event_id=str(event.id))
            return event.id
        except adapter_errors.EventAlreadyExistsError as e:
            raise service_errors.EventAlreadyExistsError from e
        except adapter_errors.RepositoryError as e:
            raise service_errors.EventRepositoryError from e

    @trace_business_logic("event_service")
    async def update_event(self, event: Event) -> None:
        span = trace.get_current_span()
        span.set_attribute("event.id", str(event.id))

        logger.info("service_updating_event", event_id=str(event.id))

        try:
            await self._event_repository.update_event(event)
            await self._kafka_producer.send_update_event(event)
            logger.info("service_event_updated", event_id=str(event.id))
        except adapter_errors.EventNotFoundError as e:
            raise service_errors.EventNotFoundError from e
        except adapter_errors.RepositoryError as e:
            raise service_errors.EventRepositoryError from e

    @trace_business_logic("event_service")
    async def delete_event(self, event_id: uuid.UUID) -> None:
        span = trace.get_current_span()
        span.set_attribute("event.id", str(event_id))

        logger.info("service_deleting_event", event_id=str(event_id))

        try:
            event = await self._event_repository.get_event_by_id(event_id)
            await self._event_repository.delete_event(event_id)
            await self._kafka_producer.send_delete_event(event)
            logger.info("service_event_deleted", event_id=str(event_id))
        except adapter_errors.EventNotFoundError as e:
            raise service_errors.EventNotFoundError from e
        except adapter_errors.RepositoryError as e:
            raise service_errors.EventRepositoryError from e

    @trace_business_logic("event_service")
    async def add_participant(
        self, event_id: uuid.UUID, participant: Participant
    ) -> None:
        span = trace.get_current_span()
        span.set_attribute("event.id", str(event_id))
        span.set_attribute("participant.id", str(participant.id))

        logger.info(
            "service_adding_participant",
            event_id=str(event_id),
            participant_id=str(participant.id),
        )

        try:
            event = await self._event_repository.get_event_by_id(event_id)
        except adapter_errors.EventNotFoundError as e:
            raise service_errors.EventNotFoundError from e

        if event.status != EventStatusEnum.OPEN:
            logger.warning(
                "service_event_not_open",
                event_id=str(event_id),
                status=str(event.status),
            )
            raise service_errors.ParticipantError(
                "Failed to add participant: event is not open"
            )

        try:
            await self._event_repository.add_participant(event_id, participant)
            await self._kafka_producer.send_participant(event, participant.id)
            logger.info(
                "service_participant_added",
                event_id=str(event_id),
                participant_id=str(participant.id),
            )
        except adapter_errors.ParticipantAlreadyExistsError as e:
            raise service_errors.ParticipantError(
                "Participant already registered"
            ) from e
        except adapter_errors.RepositoryError as e:
            raise service_errors.EventRepositoryError from e

    @trace_business_logic("event_service")
    async def get_participants(
        self,
        event_id: uuid.UUID,
        offset: Optional[int] = None,
        participant_id: Optional[uuid.UUID] = None,
        limit: int = 10,
    ) -> tuple[list[Participant], Optional[uuid.UUID]]:
        span = trace.get_current_span()
        span.set_attribute("event.id", str(event_id))
        span.set_attribute("pagination.limit", limit)
        if participant_id:
            span.set_attribute("pagination.cursor_id", str(participant_id))
        if offset is not None:
            span.set_attribute("pagination.offset", offset)

        logger.info(
            "service_receiving_participants",
            event_id=str(event_id),
            participant_id=str(participant_id) if participant_id else None,
            offset=offset,
            limit=limit,
        )

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
        except adapter_errors.EventNotFoundError as e:
            raise service_errors.EventNotFoundError from e
        except adapter_errors.ParticipantNotFoundError as e:
            raise service_errors.ParticipantNotFoundError from e
        except adapter_errors.RepositoryError as e:
            raise service_errors.EventRepositoryError from e

        raise service_errors.PaginationError(
            "Participant id or offset must be specified"
        )

    @trace_business_logic("event_service")
    async def get_participant_events(
        self,
        participant_id: uuid.UUID,
        offset: Optional[int] = None,
        event_id: Optional[uuid.UUID] = None,
        limit: int = 10,
    ) -> tuple[list[ParticipantEvent], Optional[uuid.UUID]]:
        span = trace.get_current_span()
        span.set_attribute("participant.id", str(participant_id))
        span.set_attribute("pagination.limit", limit)
        if event_id:
            span.set_attribute("pagination.cursor_id", str(event_id))
        if offset is not None:
            span.set_attribute("pagination.offset", offset)

        logger.info(
            "service_receiving_participant_events",
            participant_id=str(participant_id),
            event_id=str(event_id) if event_id else None,
            offset=offset,
            limit=limit,
        )

        if (event_id is not None) and (offset is not None):
            raise service_errors.PaginationError(
                "Event id or offset must be specified"
            ) from None

        try:
            if event_id:
                return await self._event_repository.get_participant_events_by_id(
                    participant_id, event_id, limit
                )
            if offset is not None:
                return await self._event_repository.get_participant_events_by_num(
                    participant_id, offset, limit
                )
        except adapter_errors.EventNotFoundError as e:
            raise service_errors.EventNotFoundError from e
        except adapter_errors.ParticipantNotFoundError as e:
            raise service_errors.ParticipantNotFoundError from e
        except adapter_errors.RepositoryError as e:
            raise service_errors.EventRepositoryError from e

        raise service_errors.PaginationError(
            "Event id or offset must be specified"
        )
