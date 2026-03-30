from src.service.protocols import KafkaProducer, TrackRepository


class TrackService:
    def __init__(
        self,
        track_repository: TrackRepository,
        kafka_producer: KafkaProducer,
    ) -> None: ...
