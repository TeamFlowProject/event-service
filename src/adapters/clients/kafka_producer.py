from aiokafka import AIOKafkaProducer
import uuid

from src.models import Event
from src.models.track import Track
from pydantic import BaseModel
from src.adapters.clients.topics import TRACK_CREATED, TRACK_UPDATED, TRACK_DELETED
from src.adapters.clients.dto.track import TrackCreated, TrackUpdated, TrackDeleted


def dto_serializer(dto: BaseModel) -> bytes:
    return dto.model_dump_json().encode("utf-8")


class KafkaProducerClient:
    def __init__(self, producer: AIOKafkaProducer) -> None:
        self._producer = producer

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

    async def send_create_event(self, event: Event) -> None: ...

    async def send_update_event(self, event: Event) -> None: ...

    async def send_delete_event(self, event_id: uuid.UUID) -> None: ...

    async def send_participant(
        self, event: Event, participant_id: uuid.UUID
    ) -> None: ...
