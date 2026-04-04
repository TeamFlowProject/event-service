import uuid

from aiokafka import AIOKafkaProducer

from src.models import Event
from src.models.track import Track


class KafkaProducerClient:
    def __init__(self, producer: AIOKafkaProducer) -> None:
        self._producer = producer

    async def send_create_track(self, track: Track) -> None: ...

    async def send_update_track(self, track: Track) -> None: ...

    async def send_delete_track(self, id: uuid.UUID) -> None: ...

    async def send_create_event(self, event: Event) -> None: ...

    async def send_update_event(self, event: Event) -> None: ...

    async def send_delete_event(self, event_id: uuid.UUID) -> None: ...

    async def send_participant(self, event: Event, participant_id: uuid.UUID) -> None: ...

