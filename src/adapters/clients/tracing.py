from loguru import logger
from functools import wraps
from opentelemetry import trace
from opentelemetry.trace import SpanKind
from src.core.metrics import KAFKA_MESSAGES_SENT_TOTAL
tracer = trace.get_tracer(__name__)


def trace_kafka_producer(service: str, topic: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            with tracer.start_as_current_span(
                f"kafka.send {topic}",
                kind=SpanKind.PRODUCER,
            ) as span:
                span.set_attribute("messaging.system", "kafka")
                span.set_attribute("messaging.destination", topic)
                span.set_attribute("messaging.operation", "publish")

                try:
                    result = await func(*args, **kwargs)

                    KAFKA_MESSAGES_SENT_TOTAL.labels(
                        service=service,
                        topic=topic,
                        status="success",
                    ).inc()

                    logger.info(
                        "kafka_message_sent",
                        topic=topic,
                    )
                    return result

                except Exception as e:
                    KAFKA_MESSAGES_SENT_TOTAL.labels(
                        service=service,
                        topic=topic,
                        status="error",
                    ).inc()

                    span.record_exception(e)
                    span.set_status(trace.StatusCode.ERROR, str(e))

                    logger.error(
                        "kafka_send_failed",
                        topic=topic,
                        error=str(e),
                    )
                    raise
        return wrapper
    return decorator
