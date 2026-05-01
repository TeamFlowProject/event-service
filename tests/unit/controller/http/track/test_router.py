import uuid
from datetime import datetime
from typing import cast
from unittest.mock import AsyncMock
from uuid_extensions import uuid7

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.controller.http.track.router import create_track_router
from src.models.track import Role as RoleModel, Track as TrackModel, TrackStatusEnum
from src.service.errors import EventNotFoundError, TrackNotFoundError


def make_track(**kwargs) -> TrackModel:
    track_id = cast(uuid.UUID, uuid7())
    defaults = dict(
        id=track_id,
        event_id=cast(uuid.UUID, uuid7()),
        name="Test Track",
        description="A test track description",
        max_team_count=10,
        max_participants_count=100,
        min_team_size=2,
        max_team_size=5,
        required_roles=[
            RoleModel(
                id=cast(uuid.UUID, uuid7()),
                track_id=track_id,
                name="Developer",
                description="A developer role",
                count=3,
            )
        ],
        requirements="Some requirements",
        status=TrackStatusEnum.DRAFT,
        registration_deadline=datetime(2026, 6, 1),
    )
    defaults.update(kwargs)
    return TrackModel(**defaults)  # type: ignore


def make_create_payload(**kwargs) -> dict:
    defaults = dict(
        event_id=str(cast(uuid.UUID, uuid7())),
        name="Test Track",
        description="A test track description",
        max_team_count=10,
        max_participant_count=100,
        min_team_size=2,
        max_team_size=5,
        required_roles=[
            {"name": "Developer", "description": "A developer role", "count": 3}
        ],
        requirements="Some requirements",
        status="DRAFT",
        registration_deadline="2026-06-01T00:00:00",
    )
    defaults.update(kwargs)
    return defaults


@pytest.fixture
def service():
    return AsyncMock()


@pytest.fixture
def client(service):
    app = FastAPI()
    app.include_router(create_track_router(service))
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.unit
class TestCreateTrack:
    @pytest.mark.asyncio
    async def test_returns_201_with_id(self, client, service):
        track_id = cast(uuid.UUID, uuid7())
        service.create_track.return_value = track_id

        async with client as c:
            resp = await c.post("/api/v1/track", json=make_create_payload())

        assert resp.status_code == 201
        assert resp.json() == {"id": str(track_id)}

    @pytest.mark.asyncio
    async def test_calls_service(self, client, service):
        service.create_track.return_value = cast(uuid.UUID, uuid7())

        async with client as c:
            await c.post("/api/v1/track", json=make_create_payload())

        service.create_track.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_404_when_event_not_found(self, client, service):
        from src.service.errors import EventNotFoundError

        service.create_track.side_effect = EventNotFoundError

        async with client as c:
            resp = await c.post("/api/v1/track", json=make_create_payload())

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_422_when_max_team_size_less_than_min(self, client, service):
        async with client as c:
            resp = await c.post(
                "/api/v1/track",
                json=make_create_payload(min_team_size=5, max_team_size=2),
            )

        assert resp.status_code == 422


@pytest.mark.unit
class TestGetTrack:
    @pytest.mark.asyncio
    async def test_returns_track(self, client, service):
        track = make_track()
        service.get_track.return_value = track

        async with client as c:
            resp = await c.get(f"/api/v1/track/{track.id}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(track.id)
        assert data["name"] == track.name
        assert data["status"] == track.status.value
        assert data["event_id"] == str(track.event_id)
        assert data["max_team_count"] == track.max_team_count
        assert data["max_participant_count"] == track.max_participants_count
        assert data["min_team_size"] == track.min_team_size
        assert data["max_team_size"] == track.max_team_size
        assert data["requirements"] == track.requirements
        assert data["registration_deadline"] == track.registration_deadline.isoformat()
        assert data["description"] == track.description
        assert len(data["required_roles"]) == len(track.required_roles)

    @pytest.mark.asyncio
    async def test_returns_404_when_track_not_found(self, client, service):
        service.get_track.side_effect = TrackNotFoundError

        async with client as c:
            resp = await c.get(f"/api/v1/track/{cast(uuid.UUID, uuid7())}")

        assert resp.status_code == 404


@pytest.mark.unit
class TestGetTracksByEventId:
    @pytest.mark.asyncio
    async def test_returns_tracks(self, client, service):
        event_id = cast(uuid.UUID, uuid7())
        tracks = [make_track(event_id=event_id), make_track(event_id=event_id)]
        service.get_tracks_by_event_id.return_value = tracks

        async with client as c:
            resp = await c.get(f"/api/v1/event/{event_id}/tracks")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert all(item["event_id"] == str(event_id) for item in data)

    @pytest.mark.asyncio
    async def test_returns_empty_list(self, client, service):
        service.get_tracks_by_event_id.return_value = []

        async with client as c:
            resp = await c.get(f"/api/v1/event/{cast(uuid.UUID, uuid7())}/tracks")

        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_returns_404_when_event_not_found(self, client, service):
        service.get_tracks_by_event_id.side_effect = EventNotFoundError

        async with client as c:
            resp = await c.get(f"/api/v1/event/{cast(uuid.UUID, uuid7())}/tracks")

        assert resp.status_code == 404


@pytest.mark.unit
class TestUpdateTrack:
    @pytest.mark.asyncio
    async def test_returns_204(self, client, service):
        track_id = cast(uuid.UUID, uuid7())
        payload = make_create_payload()
        payload["required_roles"] = [
            {
                "id": str(cast(uuid.UUID, uuid7())),
                "name": "Developer",
                "description": "A developer role",
                "count": 3,
            }
        ]

        async with client as c:
            resp = await c.put(f"/api/v1/track/{track_id}", json=payload)

        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_calls_service(self, client, service):
        track_id = cast(uuid.UUID, uuid7())
        payload = make_create_payload()
        payload["required_roles"] = [
            {"name": "Developer", "description": "A developer role", "count": 3}
        ]

        async with client as c:
            await c.put(f"/api/v1/track/{track_id}", json=payload)

        service.update_track.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_404_when_track_not_found(self, client, service):
        service.update_track.side_effect = TrackNotFoundError
        payload = make_create_payload()
        payload["required_roles"] = [
            {"name": "Developer", "description": "A developer role", "count": 3}
        ]

        async with client as c:
            resp = await c.put(
                f"/api/v1/track/{cast(uuid.UUID, uuid7())}", json=payload
            )

        assert resp.status_code == 404


@pytest.mark.unit
class TestDeleteTrack:
    @pytest.mark.asyncio
    async def test_returns_204(self, client, service):
        async with client as c:
            resp = await c.delete(f"/api/v1/track/{cast(uuid.UUID, uuid7())}")

        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_calls_service(self, client, service):
        track_id = cast(uuid.UUID, uuid7())

        async with client as c:
            await c.delete(f"/api/v1/track/{track_id}")

        service.delete_track.assert_called_once_with(track_id)

    @pytest.mark.asyncio
    async def test_returns_404_when_track_not_found(self, client, service):
        service.delete_track.side_effect = TrackNotFoundError

        async with client as c:
            resp = await c.delete(f"/api/v1/track/{cast(uuid.UUID, uuid7())}")

        assert resp.status_code == 404
