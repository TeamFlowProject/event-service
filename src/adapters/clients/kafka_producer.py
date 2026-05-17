from src.adapters.clients.topics import (
    ADD_PARTICIPANT,
    EVENT_CREATED,
    TRACK_CREATED,
    TRACK_UPDATED,
    TRACK_DELETED,
    EVENT_DELETED,
    EVENT_UPDATED,
)
from pydantic import BaseModel
from src.models.track import Track
from src.models import Event
from src.adapters.clients.dto.track import TrackCreated, TrackUpdated, TrackDeleted
from src.adapters.clients.dto.event import (
    EventCreated,
    EventUpdated,
    EventDeleted,
    AddParticipant,
)
from src.adapters.clients.tracing import trace_kafka_producer
from aiokafka import AIOKafkaProducer
from loguru import logger
from opentelemetry import trace, propagate
import uuid

tracer = trace.get_tracer(__name__)


def dto_serializer(dto: BaseModel) -> bytes:
    return dto.model_dump_json().encode("utf-8")


class KafkaProducerClient:
    def __init__(self, producer: AIOKafkaProducer) -> None:
        self._producer = producer

    def _build_headers(self) -> list[tuple[str, bytes]]:
        headers = {}
        propagate.inject(headers)
        return [(k, v.encode()) for k, v in headers.items()]

    async def send_create_track(self, track: Track) -> None:
        await self._producer.send_and_wait(
            topic=TRACK_CREATED,
            value=TrackCreated.from_model(track),
        )

    async def send_update_track(self, track: Track) -> None:
        await self._producer.send_and_wait(
            topic=TRACK_UPDATED,
            value=TrackUpdated.from_model(track),
        )

    async def send_delete_track(self, track: Track) -> None:
        await self._producer.send_and_wait(
            topic=TRACK_DELETED,
            value=TrackDeleted.from_model(track),
        )

    @trace_kafka_producer("event_service", EVENT_CREATED)
    async def send_create_event(self, event: Event) -> None:
        logger.info(
            "sending_event_created",
            topic=EVENT_CREATED,
            event_id=str(event.id),
        )

        await self._producer.send_and_wait(
            topic=EVENT_CREATED,
            value=EventCreated.from_model(event),
            headers=self._build_headers(),
        )

    @trace_kafka_producer("event_service", EVENT_UPDATED)
    async def send_update_event(self, event: Event) -> None:
        logger.info(
            "sending_event_updated",
            topic=EVENT_UPDATED,
            event_id=str(event.id),
        )

        await self._producer.send_and_wait(
            topic=EVENT_UPDATED,
            value=EventUpdated.from_model(event),
            headers=self._build_headers(),
        )

    @trace_kafka_producer("event_service", EVENT_DELETED)
    async def send_delete_event(self, event: Event) -> None:
        logger.info(
            "sending_event_deleted",
            topic=EVENT_DELETED,
            event_id=str(event.id),
        )

        await self._producer.send_and_wait(
            topic=EVENT_DELETED,
            value=EventDeleted.from_model(event),
            headers=self._build_headers(),
        )

    @trace_kafka_producer("event_service", ADD_PARTICIPANT)
    async def send_participant(
        self,
        event: Event,
        participant_id: uuid.UUID,
    ) -> None:
        logger.info(
            "sending_add_participant",
            topic=ADD_PARTICIPANT,
            event_id=str(event.id),
            participant_id=str(participant_id),
        )

        await self._producer.send_and_wait(
            topic=ADD_PARTICIPANT,
            value=AddParticipant.from_model(event, participant_id),
            headers=self._build_headers(),
        )
