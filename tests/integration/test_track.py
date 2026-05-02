import json
import uuid
from typing import cast

from uuid_extensions import uuid7
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from src.models.event import Event, EventTypeEnum, EventStatusEnum
from src.adapters.repository.event.postgres.repository import EventPostgresRepository
from aiokafka import AIOKafkaConsumer

from src.adapters.clients.topics import TRACK_CREATED, TRACK_DELETED, TRACK_UPDATED


@pytest_asyncio.fixture
async def event_id(pool):
    event = Event(
        id=cast(uuid.UUID, uuid7()),
        name="Test Event",
        description="Test Description",
        type=EventTypeEnum.HACKATHON,
        registration_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
        registration_end=datetime(2025, 1, 10, tzinfo=timezone.utc),
        holding_start=datetime(2025, 1, 15, tzinfo=timezone.utc),
        holding_end=datetime(2025, 1, 17, tzinfo=timezone.utc),
        created_at=datetime.now(timezone.utc),
        organizers=["Organizer 1"],
        rules="Some rules",
        faq="Some faq",
        status=EventStatusEnum.DRAFT,
    )
    await EventPostgresRepository(pool).create_event(event)
    return event.id


@pytest_asyncio.fixture
async def cleanup(pool):
    yield
    async with pool.connection() as conn:
        await conn.execute("DELETE FROM roles")
        await conn.execute("DELETE FROM tracks")
        await conn.execute("DELETE FROM events")


def _track_payload(event_id: uuid.UUID) -> dict:
    return {
        "event_id": str(event_id),
        "name": "Backend Track",
        "description": "Backend development track",
        "max_team_count": 10,
        "max_participant_count": 50,
        "min_team_size": 3,
        "max_team_size": 5,
        "required_roles": [
            {"name": "Developer", "description": "Backend developer", "count": 3},
            {"name": "Designer", "description": "UI/UX designer", "count": 1},
        ],
        "requirements": "Python experience",
        "status": "DRAFT",
        "registration_deadline": "2026-06-01T00:00:00Z",
    }


@asynccontextmanager
async def kafka_listener(bootstrap_server: str, topic: str):
    """Start a consumer positioned at the end of the topic, yield it, then stop it."""
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_server,
        group_id=f"test-group-{cast(uuid.UUID, uuid7())}",
        consumer_timeout_ms=10000,
    )
    await consumer.start()
    try:
        await consumer.seek_to_end()
        yield consumer
    finally:
        await consumer.stop()


def _parse(msg) -> dict:
    return json.loads(msg.value.decode("utf-8"))


def _assert_http_track(body: dict, payload: dict, track_id: str) -> None:
    assert body["id"] == track_id
    assert body["event_id"] == payload["event_id"]
    assert body["name"] == payload["name"]
    assert body["description"] == payload["description"]
    assert body["max_team_count"] == payload["max_team_count"]
    assert body["max_participant_count"] == payload["max_participant_count"]
    assert body["min_team_size"] == payload["min_team_size"]
    assert body["max_team_size"] == payload["max_team_size"]
    assert body["requirements"] == payload["requirements"]
    assert body["status"] == payload["status"]
    assert datetime.fromisoformat(
        body["registration_deadline"].replace("Z", "+00:00")
    ) == datetime(2026, 6, 1, tzinfo=timezone.utc)
    assert len(body["required_roles"]) == len(payload["required_roles"])
    for resp_role, req_role in zip(body["required_roles"], payload["required_roles"]):
        assert resp_role["name"] == req_role["name"]
        assert resp_role["description"] == req_role["description"]
        assert resp_role["count"] == req_role["count"]


def _assert_kafka_track(message: dict, payload: dict, track_id: str) -> None:
    assert message["id"] == track_id
    assert message["event_id"] == payload["event_id"]
    assert message["name"] == payload["name"]
    assert message["description"] == payload["description"]
    assert message["max_team_count"] == payload["max_team_count"]
    assert message["max_participants_count"] == payload["max_participant_count"]
    assert message["min_team_size"] == payload["min_team_size"]
    assert message["max_team_size"] == payload["max_team_size"]
    assert message["requirements"] == payload["requirements"]
    assert message["status"] == payload["status"]
    assert datetime.fromisoformat(
        message["registration_deadline"].replace("Z", "+00:00")
    ) == datetime(2026, 6, 1, tzinfo=timezone.utc)
    assert len(message["required_roles"]) == len(payload["required_roles"])
    for msg_role, req_role in zip(message["required_roles"], payload["required_roles"]):
        assert uuid.UUID(msg_role["id"])  # valid UUID
        assert msg_role["name"] == req_role["name"]
        assert msg_role["description"] == req_role["description"]
        assert msg_role["count"] == req_role["count"]


@pytest.mark.integration
@pytest.mark.usefixtures("cleanup")
class TestTrackFullFlow:
    @pytest.mark.asyncio
    async def test_create_track(self, http_client, kafka_container, event_id):
        payload = _track_payload(event_id)

        async with kafka_listener(kafka_container, TRACK_CREATED) as consumer:
            response = await http_client.post("/api/v1/track", json=payload)
            assert response.status_code == 201
            track_id = response.json()["id"]

            kafka_message = _parse(await consumer.getone())

        get_response = await http_client.get(f"/api/v1/track/{track_id}")
        assert get_response.status_code == 200
        _assert_http_track(get_response.json(), payload, track_id)
        _assert_kafka_track(kafka_message, payload, track_id)

    @pytest.mark.asyncio
    async def test_update_track(self, http_client, kafka_container, event_id):
        payload = _track_payload(event_id)
        create_response = await http_client.post("/api/v1/track", json=payload)
        assert create_response.status_code == 201
        track_id = create_response.json()["id"]

        existing_roles = (await http_client.get(f"/api/v1/track/{track_id}")).json()[
            "required_roles"
        ]
        updated_payload = {
            **payload,
            "name": "Updated Track",
            "status": "OPEN",
            "max_team_count": 20,
            "required_roles": [
                {
                    "id": existing_roles[0]["id"],
                    "name": "Lead Developer",
                    "description": "Senior backend developer",
                    "count": 2,
                }
            ],
        }

        async with kafka_listener(kafka_container, TRACK_UPDATED) as consumer:
            response = await http_client.put(
                f"/api/v1/track/{track_id}", json=updated_payload
            )
            assert response.status_code == 204

            kafka_message = _parse(await consumer.getone())

        get_response = await http_client.get(f"/api/v1/track/{track_id}")
        assert get_response.status_code == 200
        _assert_http_track(get_response.json(), updated_payload, track_id)
        _assert_kafka_track(kafka_message, updated_payload, track_id)

    @pytest.mark.asyncio
    async def test_delete_track(self, http_client, kafka_container, event_id):
        payload = _track_payload(event_id)
        create_response = await http_client.post("/api/v1/track", json=payload)
        assert create_response.status_code == 201
        track_id = create_response.json()["id"]

        async with kafka_listener(kafka_container, TRACK_DELETED) as consumer:
            response = await http_client.delete(f"/api/v1/track/{track_id}")
            assert response.status_code == 204

            kafka_message = _parse(await consumer.getone())

        get_response = await http_client.get(f"/api/v1/track/{track_id}")
        assert get_response.status_code == 404
        _assert_kafka_track(kafka_message, payload, track_id)

    @pytest.mark.asyncio
    async def test_full_track_lifecycle(self, http_client, kafka_container, event_id):
        payload = _track_payload(event_id)

        # create
        async with kafka_listener(kafka_container, TRACK_CREATED) as consumer:
            create_response = await http_client.post("/api/v1/track", json=payload)
            assert create_response.status_code == 201
            track_id = create_response.json()["id"]

            created_message = _parse(await consumer.getone())

        _assert_kafka_track(created_message, payload, track_id)

        # update
        existing_roles = (await http_client.get(f"/api/v1/track/{track_id}")).json()[
            "required_roles"
        ]
        updated_payload = {
            **payload,
            "name": "Updated Track",
            "status": "OPEN",
            "required_roles": [
                {
                    "id": existing_roles[0]["id"],
                    "name": "Lead Developer",
                    "description": "Senior backend developer",
                    "count": 2,
                }
            ],
        }

        async with kafka_listener(kafka_container, TRACK_UPDATED) as consumer:
            update_response = await http_client.put(
                f"/api/v1/track/{track_id}", json=updated_payload
            )
            assert update_response.status_code == 204

            updated_message = _parse(await consumer.getone())

        _assert_kafka_track(updated_message, updated_payload, track_id)

        get_response = await http_client.get(f"/api/v1/track/{track_id}")
        assert get_response.status_code == 200
        _assert_http_track(get_response.json(), updated_payload, track_id)

        #  delete
        async with kafka_listener(kafka_container, TRACK_DELETED) as consumer:
            delete_response = await http_client.delete(f"/api/v1/track/{track_id}")
            assert delete_response.status_code == 204

            deleted_message = _parse(await consumer.getone())

        _assert_kafka_track(deleted_message, updated_payload, track_id)

        get_response = await http_client.get(f"/api/v1/track/{track_id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_multiple_tracks_sends_individual_kafka_messages(
        self, http_client, kafka_container, event_id
    ):
        payload1 = _track_payload(event_id)
        payload2 = {
            **_track_payload(event_id),
            "name": "Frontend Track",
            "status": "OPEN",
        }

        async with kafka_listener(kafka_container, TRACK_CREATED) as consumer:
            r1 = await http_client.post("/api/v1/track", json=payload1)
            r2 = await http_client.post("/api/v1/track", json=payload2)
            assert r1.status_code == 201
            assert r2.status_code == 201
            track_id1 = r1.json()["id"]
            track_id2 = r2.json()["id"]

            msg1 = _parse(await consumer.getone())
            msg2 = _parse(await consumer.getone())

        assert msg1["id"] == track_id1
        _assert_kafka_track(msg1, payload1, track_id1)

        assert msg2["id"] == track_id2
        _assert_kafka_track(msg2, payload2, track_id2)

    @pytest.mark.asyncio
    async def test_update_preserves_existing_role_id(
        self, http_client, kafka_container, event_id
    ):
        payload = _track_payload(event_id)
        create_response = await http_client.post("/api/v1/track", json=payload)
        assert create_response.status_code == 201
        track_id = create_response.json()["id"]

        original_roles = (await http_client.get(f"/api/v1/track/{track_id}")).json()[
            "required_roles"
        ]
        existing_role_id = original_roles[0]["id"]

        updated_payload = {
            **payload,
            "required_roles": [
                {
                    "id": existing_role_id,
                    "name": "Senior Developer",
                    "description": "Updated description",
                    "count": 5,
                }
            ],
        }

        async with kafka_listener(kafka_container, TRACK_UPDATED) as consumer:
            response = await http_client.put(
                f"/api/v1/track/{track_id}", json=updated_payload
            )
            assert response.status_code == 204

            kafka_message = _parse(await consumer.getone())

        get_response = await http_client.get(f"/api/v1/track/{track_id}")
        assert get_response.status_code == 200
        updated_roles = get_response.json()["required_roles"]
        assert len(updated_roles) == 1
        assert updated_roles[0]["id"] == existing_role_id
        assert updated_roles[0]["name"] == "Senior Developer"
        assert updated_roles[0]["count"] == 5

        assert kafka_message["required_roles"][0]["id"] == existing_role_id

    @pytest.mark.asyncio
    async def test_get_tracks_by_event_id(self, http_client, event_id):
        payload1 = _track_payload(event_id)
        payload2 = {**_track_payload(event_id), "name": "Frontend Track"}

        r1 = await http_client.post("/api/v1/track", json=payload1)
        r2 = await http_client.post("/api/v1/track", json=payload2)
        assert r1.status_code == 201
        assert r2.status_code == 201

        response = await http_client.get(f"/api/v1/event/{event_id}/tracks")
        assert response.status_code == 200
        tracks = response.json()
        assert len(tracks) == 2
        names = {t["name"] for t in tracks}
        assert names == {"Backend Track", "Frontend Track"}
        for track in tracks:
            assert len(track["required_roles"]) == 2

    @pytest.mark.asyncio
    async def test_get_tracks_by_unknown_event_id_returns_empty(self, http_client):
        response = await http_client.get(
            f"/api/v1/event/{cast(uuid.UUID, uuid7())}/tracks"
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_create_track_with_invalid_payload_returns_422(
        self, http_client, event_id
    ):
        invalid_payload = {
            "event_id": str(event_id),
            "name": "",
            "description": "desc",
            "max_team_count": 10,
            "max_participant_count": 50,
            "min_team_size": 3,
            "max_team_size": 5,
            "required_roles": [{"name": "Dev", "description": "desc", "count": 1}],
            "requirements": "Python",
            "status": "DRAFT",
            "registration_deadline": "2026-06-01T00:00:00Z",
        }
        response = await http_client.post("/api/v1/track", json=invalid_payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_track_with_invalid_team_size_returns_422(
        self, http_client, event_id
    ):
        invalid_payload = {
            **_track_payload(event_id),
            "min_team_size": 5,
            "max_team_size": 3,
        }
        response = await http_client.post("/api/v1/track", json=invalid_payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_track_with_unknown_event_id_returns_404(self, http_client):
        payload = _track_payload(cast(uuid.UUID, uuid7()))

        response = await http_client.post("/api/v1/track", json=payload)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_track_not_found_returns_404(self, http_client):
        response = await http_client.get(f"/api/v1/track/{cast(uuid.UUID, uuid7())}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_track_not_found_returns_404(self, http_client, event_id):
        payload = _track_payload(event_id)
        response = await http_client.put(
            f"/api/v1/track/{cast(uuid.UUID, uuid7())}", json=payload
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_track_not_found_returns_404(self, http_client):
        response = await http_client.delete(f"/api/v1/track/{cast(uuid.UUID, uuid7())}")
        assert response.status_code == 404
