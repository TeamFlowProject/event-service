import uuid
from datetime import datetime
from typing import cast
from unittest.mock import AsyncMock
from uuid_extensions import uuid7

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.controller.http.event.router import create_event_router
from src.models.event import (
    Event as EventModel,
    EventStatusEnum,
    EventTypeEnum,
    Participant as ParticipantModel,
    ParticipantEvent as ParticipantEventModel,
)
from src.models.track import Role as RoleModel
from src.service.errors import (
    EventNotFoundError,
    PaginationError,
    ParticipantError,
    ParticipantNotFoundError,
)


def make_event(**kwargs) -> EventModel:
    defaults = dict(
        id=cast(uuid.UUID, uuid7()),
        name="Test Event",
        description="Test event description",
        type=EventTypeEnum.HACKATHON,
        registration_start=datetime(2026, 1, 1),
        registration_end=datetime(2026, 1, 10),
        holding_start=datetime(2026, 1, 11),
        holding_end=datetime(2026, 1, 12),
        created_at=datetime(2026, 1, 1),
        organizers=["Org A"],
        rules="Some rules",
        faq="Some faq",
        status=EventStatusEnum.DRAFT,
    )
    defaults.update(kwargs)
    return EventModel(**defaults)  # type: ignore[arg-type]


def make_participant(**kwargs) -> ParticipantModel:
    defaults = dict(
        id=cast(uuid.UUID, uuid7()),
        event_id=cast(uuid.UUID, uuid7()),
        name="Ivan",
        surname="Ivanov",
        patronymic="Ivanovich",
        have_team=False,
    )
    defaults.update(kwargs)
    return ParticipantModel(**defaults)  # type: ignore[arg-type]


def make_participant_event(**kwargs) -> ParticipantEventModel:
    defaults = dict(
        id=cast(uuid.UUID, uuid7()),
        name="Test Event",
        description="Test event description",
        status=EventStatusEnum.OPEN,
        total_places=100,
        current_participants=15,
        tracks_count=3,
        registration_start=datetime(2026, 1, 1),
        registration_end=datetime(2026, 1, 10),
        holding_start=datetime(2026, 1, 11),
        holding_end=datetime(2026, 1, 12),
        user_role=RoleModel(
            id=cast(uuid.UUID, uuid7()),
            track_id=cast(uuid.UUID, uuid7()),
            name="PARTICIPANT",
            description="",
            count=0,
        ),
    )

    defaults.update(kwargs)
    return ParticipantEventModel(**defaults)  # type: ignore[arg-type]


def make_create_payload(**kwargs) -> dict:
    defaults = dict(
        name="Test Event",
        description="Test event description",
        type="HACKATHON",
        registration_start="2026-01-01T00:00:00",
        registration_end="2026-01-10T00:00:00",
        holding_start="2026-01-11T00:00:00",
        holding_end="2026-01-12T00:00:00",
        organizers=["Org A"],
        rules="Some rules",
        faq="Some faq",
    )
    defaults.update(kwargs)
    return defaults


@pytest.fixture
def service():
    return AsyncMock()


@pytest.fixture
def client(service):
    app = FastAPI()
    app.include_router(create_event_router(service))
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.unit
class TestCreateEvent:
    @pytest.mark.asyncio
    async def test_returns_201_with_id(self, client, service):
        event_id = cast(uuid.UUID, uuid7())
        service.create_event.return_value = event_id

        async with client as c:
            resp = await c.post("/api/v1/events", json=make_create_payload())

        assert resp.status_code == 201
        assert resp.json() == {"id": str(event_id)}

    @pytest.mark.asyncio
    async def test_calls_service(self, client, service):
        service.create_event.return_value = cast(uuid.UUID, uuid7())

        async with client as c:
            await c.post("/api/v1/events", json=make_create_payload())

        service.create_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_422_when_holding_start_before_registration_end(
        self, client, service
    ):
        async with client as c:
            resp = await c.post(
                "/api/v1/events",
                json=make_create_payload(
                    registration_end="2026-01-12T00:00:00",
                    holding_start="2026-01-11T00:00:00",
                ),
            )

        assert resp.status_code == 422


@pytest.mark.unit
class TestGetEvent:
    @pytest.mark.asyncio
    async def test_returns_event(self, client, service):
        event = make_event()
        service.get_event_by_id.return_value = event

        async with client as c:
            resp = await c.get(f"/api/v1/events/{event.id}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(event.id)
        assert data["name"] == event.name
        assert data["status"] == event.status.value
        assert data["faq"] == event.faq

    @pytest.mark.asyncio
    async def test_returns_404_when_event_not_found(self, client, service):
        service.get_event_by_id.side_effect = EventNotFoundError

        async with client as c:
            resp = await c.get(f"/api/v1/events/{cast(uuid.UUID, uuid7())}")

        assert resp.status_code == 404


@pytest.mark.unit
class TestUpdateEvent:
    @pytest.mark.asyncio
    async def test_returns_200(self, client, service):
        event_id = cast(uuid.UUID, uuid7())
        current_event = make_event(id=event_id)
        service.get_event_by_id.return_value = current_event

        async with client as c:
            resp = await c.put(
                f"/api/v1/events/{event_id}",
                json={"name": "Updated Event"},
            )

        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Event"

    @pytest.mark.asyncio
    async def test_calls_service(self, client, service):
        event_id = cast(uuid.UUID, uuid7())
        service.get_event_by_id.return_value = make_event(id=event_id)

        async with client as c:
            await c.put(f"/api/v1/events/{event_id}", json={"name": "Updated Event"})

        service.update_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_404_when_event_not_found(self, client, service):
        service.get_event_by_id.side_effect = EventNotFoundError

        async with client as c:
            resp = await c.put(
                f"/api/v1/events/{cast(uuid.UUID, uuid7())}", json={"name": "x"}
            )

        assert resp.status_code == 404


@pytest.mark.unit
class TestDeleteEvent:
    @pytest.mark.asyncio
    async def test_returns_204(self, client, service):
        async with client as c:
            resp = await c.delete(f"/api/v1/events/{cast(uuid.UUID, uuid7())}")

        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_calls_service(self, client, service):
        event_id = cast(uuid.UUID, uuid7())

        async with client as c:
            await c.delete(f"/api/v1/events/{event_id}")

        service.delete_event.assert_called_once_with(event_id)

    @pytest.mark.asyncio
    async def test_returns_404_when_event_not_found(self, client, service):
        service.delete_event.side_effect = EventNotFoundError

        async with client as c:
            resp = await c.delete(f"/api/v1/events/{cast(uuid.UUID, uuid7())}")

        assert resp.status_code == 404


@pytest.mark.unit
class TestGetEvents:
    @pytest.mark.asyncio
    async def test_returns_events_page(self, client, service):
        event_1 = make_event()
        event_2 = make_event()
        next_cursor = cast(uuid.UUID, uuid7())
        service.get_events_page.return_value = ([event_1, event_2], next_cursor)

        async with client as c:
            resp = await c.get("/api/v1/events", params={"offset": 0, "limit": 2})

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["next_cursor"] == str(next_cursor)

    @pytest.mark.asyncio
    async def test_returns_400_when_pagination_error(self, client, service):
        service.get_events_page.side_effect = PaginationError("bad pagination")

        async with client as c:
            resp = await c.get("/api/v1/events")

        assert resp.status_code == 400


@pytest.mark.unit
class TestCreateParticipant:
    @pytest.mark.asyncio
    async def test_returns_201_with_id(self, client, service):
        event_id = cast(uuid.UUID, uuid7())
        payload = {
            "name": "Ivan",
            "surname": "Ivanov",
            "patronymic": "Ivanovich",
            "have_team": False,
        }

        async with client as c:
            resp = await c.post(f"/api/v1/events/{event_id}/participants", json=payload)

        assert resp.status_code == 201
        assert "id" in resp.json()

    @pytest.mark.asyncio
    async def test_calls_service(self, client, service):
        event_id = cast(uuid.UUID, uuid7())
        payload = {
            "name": "Ivan",
            "surname": "Ivanov",
            "patronymic": "Ivanovich",
            "have_team": False,
        }

        async with client as c:
            await c.post(f"/api/v1/events/{event_id}/participants", json=payload)

        service.add_participant.assert_called_once()
        call_event_id, call_participant = service.add_participant.call_args.args
        assert call_event_id == event_id
        assert call_participant.event_id == event_id
        assert call_participant.name == payload["name"]
        assert call_participant.surname == payload["surname"]
        assert call_participant.patronymic == payload["patronymic"]
        assert call_participant.have_team is payload["have_team"]

    @pytest.mark.asyncio
    async def test_returns_404_when_event_not_found(self, client, service):
        service.add_participant.side_effect = EventNotFoundError
        payload = {"name": "Ivan", "surname": "Ivanov", "patronymic": "Ivanovich"}

        async with client as c:
            resp = await c.post(
                f"/api/v1/events/{cast(uuid.UUID, uuid7())}/participants", json=payload
            )

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_400_when_participant_error(self, client, service):
        service.add_participant.side_effect = ParticipantError("bad participant")
        payload = {"name": "Ivan", "surname": "Ivanov", "patronymic": "Ivanovich"}

        async with client as c:
            resp = await c.post(
                f"/api/v1/events/{cast(uuid.UUID, uuid7())}/participants", json=payload
            )

        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_returns_422_when_payload_is_invalid(self, client, service):
        payload = {"name": "", "surname": "Ivanov", "patronymic": "Ivanovich"}

        async with client as c:
            resp = await c.post(
                f"/api/v1/events/{cast(uuid.UUID, uuid7())}/participants", json=payload
            )

        assert resp.status_code == 422


@pytest.mark.unit
class TestGetParticipants:
    @pytest.mark.asyncio
    async def test_returns_participants_page(self, client, service):
        event_id = cast(uuid.UUID, uuid7())
        participant = make_participant(event_id=event_id)
        cursor = cast(uuid.UUID, uuid7())
        service.get_participants.return_value = ([participant], cursor)

        async with client as c:
            resp = await c.get(f"/api/v1/events/{event_id}/participants")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == str(participant.id)
        assert data["items"][0]["event_id"] == str(event_id)
        assert data["next_cursor"] == str(cursor)

    @pytest.mark.asyncio
    async def test_returns_404_when_event_not_found(self, client, service):
        service.get_participants.side_effect = EventNotFoundError

        async with client as c:
            resp = await c.get(
                f"/api/v1/events/{cast(uuid.UUID, uuid7())}/participants"
            )

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_404_when_participant_not_found(self, client, service):
        service.get_participants.side_effect = ParticipantNotFoundError

        async with client as c:
            resp = await c.get(
                f"/api/v1/events/{cast(uuid.UUID, uuid7())}/participants"
            )

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_400_when_pagination_error(self, client, service):
        service.get_participants.side_effect = PaginationError("bad pagination")

        async with client as c:
            resp = await c.get(
                f"/api/v1/events/{cast(uuid.UUID, uuid7())}/participants"
            )

        assert resp.status_code == 400


@pytest.mark.unit
class TestGetParticipantEvents:
    @pytest.mark.asyncio
    async def test_returns_participant_events_page(self, client, service):
        participant_id = cast(uuid.UUID, uuid7())
        event = make_participant_event()
        cursor = cast(uuid.UUID, uuid7())
        service.get_participant_events.return_value = ([event], cursor)

        async with client as c:
            resp = await c.get(
                f"/api/v1/participants/{participant_id}/events",
                params={"offset": 0, "limit": 10},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == str(event.id)
        assert data["items"][0]["name"] == event.name
        assert data["items"][0]["total_places"] == event.total_places
        assert data["items"][0]["current_participants"] == event.current_participants
        assert data["items"][0]["tracks_count"] == event.tracks_count
        assert event.user_role is not None
        assert data["items"][0]["user_role"] == {
            "id": str(event.user_role.id),
            "track_id": str(event.user_role.track_id),
            "name": event.user_role.name,
            "description": event.user_role.description,
            "count": event.user_role.count,
        }
        assert data["next_cursor"] == str(cursor)

    @pytest.mark.asyncio
    async def test_calls_service_with_query_params(self, client, service):
        participant_id = cast(uuid.UUID, uuid7())
        service.get_participant_events.return_value = ([], None)
        event_id = cast(uuid.UUID, uuid7())

        async with client as c:
            await c.get(
                f"/api/v1/participants/{participant_id}/events",
                params={"event_id": str(event_id), "limit": 10},
            )

        service.get_participant_events.assert_called_once_with(
            participant_id=participant_id,
            event_id=event_id,
            offset=None,
            limit=10,
        )

    @pytest.mark.asyncio
    async def test_returns_400_when_pagination_error(self, client, service):
        service.get_participant_events.side_effect = PaginationError("bad pagination")

        async with client as c:
            resp = await c.get(
                f"/api/v1/participants/{cast(uuid.UUID, uuid7())}/events"
            )

        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_returns_404_when_participant_not_found(self, client, service):
        service.get_participant_events.side_effect = ParticipantNotFoundError

        async with client as c:
            resp = await c.get(
                f"/api/v1/participants/{cast(uuid.UUID, uuid7())}/events"
            )

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_404_when_event_not_found(self, client, service):
        service.get_participant_events.side_effect = EventNotFoundError

        async with client as c:
            resp = await c.get(
                f"/api/v1/participants/{cast(uuid.UUID, uuid7())}/events",
                params={"event_id": str(cast(uuid.UUID, uuid7()))},
            )

        assert resp.status_code == 404
