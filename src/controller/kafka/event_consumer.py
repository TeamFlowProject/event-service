from aiokafka import AIOKafkaConsumer

from src.controller.kafka.protocols import EventService


class EventKafkaConsumer:
    def __init__(
        self, consumer: AIOKafkaConsumer, event_service: EventService
    ) -> None: ...

    async def start(self) -> None: ...
