import json

from aiokafka import AIOKafkaConsumer
from aiokafka.structs import TopicPartition
from loguru import logger
from opentelemetry import propagate, trace
from opentelemetry.trace import SpanKind
from pydantic import ValidationError

import src.service.errors as service_errors
from src.adapters.clients.topics import (
    CONFIRMATION_TEAM_BECAME_INVALID,
    CONFIRMATION_TEAM_CONFIRMED,
    CONFIRMATION_TEAM_REJECTED,
    CONFIRMATION_TEAM_VALIDATED,
)
from src.controller.kafka.dto import TeamConfirmationEvent
from src.controller.kafka.protocols import TeamService
from src.core.metrics import KAFKA_MESSAGES_CONSUMED_TOTAL
from src.models.team import TeamStatusEnum

tracer = trace.get_tracer(__name__)

_SERVICE = "event_service"

_STATUS_BY_TOPIC: dict[str, TeamStatusEnum] = {
    CONFIRMATION_TEAM_VALIDATED: TeamStatusEnum.VALIDATED,
    CONFIRMATION_TEAM_CONFIRMED: TeamStatusEnum.CONFIRMED,
    CONFIRMATION_TEAM_REJECTED: TeamStatusEnum.REJECTED,
    CONFIRMATION_TEAM_BECAME_INVALID: TeamStatusEnum.INVALID,
}

TOPICS: list[str] = list(_STATUS_BY_TOPIC)

_SKIP_ERRORS = (service_errors.TeamNotFoundError,)


class EventKafkaConsumer:
    def __init__(self, consumer: AIOKafkaConsumer, team_service: TeamService) -> None:
        self._consumer = consumer
        self._team_service = team_service

    async def start(self) -> None:
        await self._consumer.start()
        logger.info("kafka_consumer_started", topics=TOPICS)
        try:
            async for msg in self._consumer:
                logger.debug(
                    "kafka_message_received",
                    topic=msg.topic,
                    partition=msg.partition,
                    offset=msg.offset,
                )
                await self._process(msg)
        finally:
            await self._consumer.stop()
            logger.info("kafka_consumer_stopped")

    @staticmethod
    def _extract_context(headers):
        carrier = {key: value.decode() for key, value in (headers or [])}
        return propagate.extract(carrier)

    async def _process(self, msg) -> None:
        status = _STATUS_BY_TOPIC.get(msg.topic)
        if status is None:
            logger.warning("kafka_unhandled_topic", topic=msg.topic)
            await self._consumer.commit()
            return

        try:
            payload = json.loads(msg.value)
            event = TeamConfirmationEvent.model_validate(payload)
        except (json.JSONDecodeError, ValidationError, TypeError) as e:
            logger.error(
                "kafka_skip_malformed_message",
                topic=msg.topic,
                offset=msg.offset,
                error=str(e),
            )
            KAFKA_MESSAGES_CONSUMED_TOTAL.labels(
                service=_SERVICE, topic=msg.topic, status="error"
            ).inc()
            await self._consumer.commit()
            return

        team_id = event.payload.application_id
        context = self._extract_context(msg.headers)
        with tracer.start_as_current_span(
            f"kafka.consume {msg.topic}",
            kind=SpanKind.CONSUMER,
            context=context,
        ) as span:
            span.set_attribute("messaging.system", "kafka")
            span.set_attribute("messaging.source", msg.topic)
            span.set_attribute("messaging.operation", "process")
            span.set_attribute("team.id", str(team_id))
            span.set_attribute("team.status", status.value)

            try:
                await self._team_service.change_team_status(team_id, status)
                KAFKA_MESSAGES_CONSUMED_TOTAL.labels(
                    service=_SERVICE, topic=msg.topic, status="success"
                ).inc()
                logger.info(
                    "kafka_team_status_changed",
                    topic=msg.topic,
                    team_id=str(team_id),
                    status=status.value,
                )
                await self._consumer.commit()

            except _SKIP_ERRORS as e:
                span.record_exception(e)
                logger.warning(
                    "kafka_skip_message",
                    topic=msg.topic,
                    offset=msg.offset,
                    team_id=str(team_id),
                    error=str(e),
                )
                KAFKA_MESSAGES_CONSUMED_TOTAL.labels(
                    service=_SERVICE, topic=msg.topic, status="error"
                ).inc()
                await self._consumer.commit()

            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.StatusCode.ERROR, str(e))
                logger.exception(
                    "kafka_process_failed",
                    topic=msg.topic,
                    offset=msg.offset,
                    team_id=str(team_id),
                )
                KAFKA_MESSAGES_CONSUMED_TOTAL.labels(
                    service=_SERVICE, topic=msg.topic, status="error"
                ).inc()
                self._consumer.seek(
                    TopicPartition(msg.topic, msg.partition), msg.offset
                )
