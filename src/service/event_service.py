from src.service.protocols import EventRepository, KafkaProducer


class EventService:
    def __init__(
        self,
        event_repository: EventRepository,
        kafka_producer: KafkaProducer,
    ) -> None: ...
