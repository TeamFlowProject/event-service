import json
import uuid
from datetime import datetime, timezone

import pytest
from aiokafka import AIOKafkaConsumer

from src.adapters.clients.topics import TRACK_CREATED, TRACK_UPDATED, TRACK_DELETED
from src.models.track import Role, Track, TrackStatusEnum


def _make_track() -> Track:
    track_id = uuid.uuid4()
    return Track(
        id=track_id,
        event_id=uuid.uuid4(),
        name="Backend Track",
        description="Backend development track",
        max_team_count=10,
        max_participants_count=50,
        min_team_size=3,
        max_team_size=5,
        required_roles=[
            Role(
                id=uuid.uuid4(),
                track_id=track_id,
                name="Developer",
                description="Backend developer",
                count=3,
            ),
        ],
        requirements="Python experience",
        status=TrackStatusEnum.DRAFT,
        registration_deadline=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )


async def _consume_one(bootstrap_server: str, topic: str) -> dict:
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_server,
        auto_offset_reset="earliest",
        group_id=f"test-group-{uuid.uuid4()}",
        consumer_timeout_ms=10000,
    )
    await consumer.start()
    try:
        msg = await consumer.getone()
        return json.loads(msg.value.decode("utf-8"))  # type: ignore
    finally:
        await consumer.stop()


def _assert_track_message(message: dict, track: Track) -> None:
    assert message["id"] == str(track.id)
    assert message["event_id"] == str(track.event_id)
    assert message["name"] == track.name
    assert message["description"] == track.description
    assert message["max_team_count"] == track.max_team_count
    assert message["max_participants_count"] == track.max_participants_count
    assert message["min_team_size"] == track.min_team_size
    assert message["max_team_size"] == track.max_team_size
    assert message["requirements"] == track.requirements
    assert message["status"] == track.status.value
    assert (
        datetime.fromisoformat(message["registration_deadline"].replace("Z", "+00:00"))
        == track.registration_deadline
    )

    assert len(message["required_roles"]) == len(track.required_roles)
    for msg_role, model_role in zip(message["required_roles"], track.required_roles):
        assert msg_role["id"] == str(model_role.id)
        assert msg_role["name"] == model_role.name
        assert msg_role["description"] == model_role.description
        assert msg_role["count"] == model_role.count


@pytest.mark.integration
class TestKafkaProducerClient:
    @pytest.mark.asyncio
    async def test_send_create_track(self, kafka_producer_client, kafka_container):
        track = _make_track()

        await kafka_producer_client.send_create_track(track)

        message = await _consume_one(kafka_container, TRACK_CREATED)
        _assert_track_message(message, track)

    @pytest.mark.asyncio
    async def test_send_update_track(self, kafka_producer_client, kafka_container):
        track = _make_track()
        track.name = "Updated Track"
        track.status = TrackStatusEnum.OPEN

        await kafka_producer_client.send_update_track(track)

        message = await _consume_one(kafka_container, TRACK_UPDATED)
        _assert_track_message(message, track)

    @pytest.mark.asyncio
    async def test_send_delete_track(self, kafka_producer_client, kafka_container):
        track = _make_track()

        await kafka_producer_client.send_delete_track(track)

        message = await _consume_one(kafka_container, TRACK_DELETED)
        _assert_track_message(message, track)
