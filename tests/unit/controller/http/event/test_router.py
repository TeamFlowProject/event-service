import uuid
from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.controller.http.event.router import create_event_router
from src.models.event import (
    Event as EventModel,
    EventStatusEnum,
    EventTypeEnum,
    Participant as ParticipantModel,
)
from src.service.errors import (
    EventNotFoundError,
    PaginationError,
    ParticipantNotFoundError,
)


def make_event(**kwargs) -> EventModel:
    defaults = dict(
        id=uuid.uuid4(),
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
        id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        name="Ivan",
        surname="Ivanov",
        patronymic="Ivanovich",
        have_team=False,
    )
    defaults.update(kwargs)
    return ParticipantModel(**defaults)  # type: ignore[arg-type]


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
        event_id = uuid.uuid4()
        service.create_event.return_value = event_id

        async with client as c:
            resp = await c.post("/api/v1/events", json=make_create_payload())

        assert resp.status_code == 201
        assert resp.json() == {"id": str(event_id)}

    @pytest.mark.asyncio
    async def test_calls_service(self, client, service):
        service.create_event.return_value = uuid.uuid4()

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
            resp = await c.get(f"/api/v1/events/{uuid.uuid4()}")

        assert resp.status_code == 404


@pytest.mark.unit
class TestUpdateEvent:
    @pytest.mark.asyncio
    async def test_returns_200(self, client, service):
        event_id = uuid.uuid4()
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
        event_id = uuid.uuid4()
        service.get_event_by_id.return_value = make_event(id=event_id)

        async with client as c:
            await c.put(f"/api/v1/events/{event_id}", json={"name": "Updated Event"})

        service.update_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_404_when_event_not_found(self, client, service):
        service.get_event_by_id.side_effect = EventNotFoundError

        async with client as c:
            resp = await c.put(f"/api/v1/events/{uuid.uuid4()}", json={"name": "x"})

        assert resp.status_code == 404


@pytest.mark.unit
class TestDeleteEvent:
    @pytest.mark.asyncio
    async def test_returns_204(self, client, service):
        async with client as c:
            resp = await c.delete(f"/api/v1/events/{uuid.uuid4()}")

        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_calls_service(self, client, service):
        event_id = uuid.uuid4()

        async with client as c:
            await c.delete(f"/api/v1/events/{event_id}")

        service.delete_event.assert_called_once_with(event_id)

    @pytest.mark.asyncio
    async def test_returns_404_when_event_not_found(self, client, service):
        service.delete_event.side_effect = EventNotFoundError

        async with client as c:
            resp = await c.delete(f"/api/v1/events/{uuid.uuid4()}")

        assert resp.status_code == 404


@pytest.mark.unit
class TestGetEvents:
    @pytest.mark.asyncio
    async def test_returns_events_page(self, client, service):
        event_1 = make_event()
        event_2 = make_event()
        next_cursor = uuid.uuid4()
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
class TestGetParticipants:
    @pytest.mark.asyncio
    async def test_returns_participants_page(self, client, service):
        event_id = uuid.uuid4()
        participant = make_participant(event_id=event_id)
        cursor = uuid.uuid4()
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
            resp = await c.get(f"/api/v1/events/{uuid.uuid4()}/participants")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_404_when_participant_not_found(self, client, service):
        service.get_participants.side_effect = ParticipantNotFoundError

        async with client as c:
            resp = await c.get(f"/api/v1/events/{uuid.uuid4()}/participants")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_400_when_pagination_error(self, client, service):
        service.get_participants.side_effect = PaginationError("bad pagination")

        async with client as c:
            resp = await c.get(f"/api/v1/events/{uuid.uuid4()}/participants")

        assert resp.status_code == 400
