import uuid

from aiokafka import AIOKafkaProducer

from src.models.track import Track


class KafkaProducerClient:
    def __init__(self, producer: AIOKafkaProducer) -> None:
        self._producer = producer

    async def send_create_track(self, track: Track) -> None: ...

    async def send_update_track(self, track: Track) -> None: ...

    async def send_delete_track(self, id: uuid.UUID) -> None: ...
