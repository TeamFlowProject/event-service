from aiokafka import AIOKafkaProducer


class KafkaProducerClient:
    def __init__(self, producer: AIOKafkaProducer) -> None: ...
