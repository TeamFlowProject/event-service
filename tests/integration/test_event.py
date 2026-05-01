import uuid
from datetime import datetime, timezone
from typing import cast

from uuid_extensions import uuid7

import pytest

from src.models.event import Event, EventStatusEnum, EventTypeEnum, Participant


def _make_event() -> Event:
    event_id = cast(uuid.UUID, uuid7())
    return Event(
        id=event_id,
        name=f"Event {event_id}",
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
        status=EventStatusEnum.OPEN,
    )


def _make_participant(participant_id: uuid.UUID, event_id: uuid.UUID) -> Participant:
    return Participant(
        id=participant_id,
        event_id=event_id,
        name="Ivan",
        surname="Ivanov",
        patronymic="Ivanovich",
        have_team=False,
    )


async def cleanup_db(pool):
    """Clean up database after test."""
    async with pool.connection() as conn:
        await conn.execute("DELETE FROM event_participants")
        await conn.execute("DELETE FROM participants")
        await conn.execute("DELETE FROM roles")
        await conn.execute("DELETE FROM tracks")
        await conn.execute("DELETE FROM events")


@pytest.mark.integration
class TestParticipantEventsEndpoint:
    @pytest.mark.asyncio
    async def test_returns_participant_events_with_required_fields(
        self, http_client, event_repository, pool
    ):
        participant_id = cast(uuid.UUID, uuid7())
        for _ in range(15):
            event = _make_event()
            await event_repository.create_event(event)
            await event_repository.add_participant(
                event.id, _make_participant(participant_id, event.id)
            )

        try:
            response = await http_client.get(
                f"/api/v1/participants/{participant_id}/events", params={"offset": 0}
            )
            assert response.status_code == 200
            payload = response.json()

            assert len(payload["items"]) == 10
            first_item = payload["items"][0]
            assert set(first_item.keys()) == {
                "id",
                "name",
                "description",
                "status",
                "total_places",
                "current_participants",
                "tracks_count",
                "registration_start",
                "registration_end",
                "holding_start",
                "holding_end",
                "user_role",
            }
            assert first_item["user_role"] == "PARTICIPANT"
        finally:
            await cleanup_db(pool)

    @pytest.mark.asyncio
    async def test_paginates_participant_events_with_offset_and_cursor(
        self, http_client, event_repository, pool
    ):
        participant_id = cast(uuid.UUID, uuid7())
        for _ in range(15):
            event = _make_event()
            await event_repository.create_event(event)
            await event_repository.add_participant(
                event.id, _make_participant(participant_id, event.id)
            )

        try:
            first_page_response = await http_client.get(
                f"/api/v1/participants/{participant_id}/events",
                params={"offset": 0, "limit": 10},
            )
            assert first_page_response.status_code == 200
            first_page = first_page_response.json()

            second_page_response = await http_client.get(
                f"/api/v1/participants/{participant_id}/events",
                params={"event_id": first_page["next_cursor"], "limit": 10},
            )
            assert second_page_response.status_code == 200
            second_page = second_page_response.json()

            assert len(first_page["items"]) == 10
            assert len(second_page["items"]) == 5

            first_page_ids = {item["id"] for item in first_page["items"]}
            second_page_ids = {item["id"] for item in second_page["items"]}
            assert first_page_ids.isdisjoint(second_page_ids)
        finally:
            await cleanup_db(pool)
