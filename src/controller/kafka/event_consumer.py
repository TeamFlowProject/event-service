from aiokafka import AIOKafkaConsumer

from src.service.event_service import EventService


class EventKafkaConsumer:
    def __init__(self, consumer: AIOKafkaConsumer, event_service: EventService) -> None: ...

    async def start(self) -> None: ...
