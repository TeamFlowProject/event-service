import uuid
from datetime import datetime, timezone

import pytest

from src.adapters.repository.errors import EventNotFoundError
from src.models.event import Event, EventTypeEnum, EventStatusEnum


def _make_event() -> Event:
    return Event(
        id=uuid.uuid4(),
        name="Test Event",
        description="Test Description",
        type=EventTypeEnum.HACKATHON,
        registration_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
        registration_end=datetime(2025, 1, 10, tzinfo=timezone.utc),
        holding_start=datetime(2025, 1, 15, tzinfo=timezone.utc),
        holding_end=datetime(2025, 1, 17, tzinfo=timezone.utc),
        created_at=datetime.now(timezone.utc),
        organizers=["Organizer 1", "Organizer 2"],
        rules="Some rules",
        faq="Some faq",
        status=EventStatusEnum.DRAFT,
    )


@pytest.mark.integration
@pytest.mark.usefixtures("cleanup")
class TestEventPostgresRepository:
    @pytest.mark.asyncio
    async def test_create_and_get_event(self, event_repository):
        event = _make_event()

        await event_repository.create_event(event)
        result = await event_repository.get_event_by_id(event.id)

        assert result.id == event.id
        assert result.name == event.name
        assert result.description == event.description
        assert result.type == event.type
        assert result.registration_start == event.registration_start
        assert result.registration_end == event.registration_end
        assert result.holding_start == event.holding_start
        assert result.holding_end == event.holding_end
        assert result.created_at == event.created_at
        assert result.organizers == event.organizers
        assert result.rules == event.rules
        assert result.faq == event.faq
        assert result.status == EventStatusEnum.DRAFT

    @pytest.mark.asyncio
    async def test_get_event_not_found(self, event_repository):
        with pytest.raises(EventNotFoundError):
            await event_repository.get_event_by_id(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_update_event(self, event_repository):
        event = _make_event()
        await event_repository.create_event(event)

        event.name = "Updated Event"
        event.status = EventStatusEnum.OPEN
        event.rules = "New rules"

        await event_repository.update_event(event)
        result = await event_repository.get_event_by_id(event.id)

        assert result.name == "Updated Event"
        assert result.status == EventStatusEnum.OPEN
        assert result.rules == "New rules"
        assert result.description == event.description

    @pytest.mark.asyncio
    async def test_delete_event(self, event_repository):
        event = _make_event()
        await event_repository.create_event(event)

        await event_repository.delete_event(event.id)

        with pytest.raises(EventNotFoundError):
            await event_repository.get_event_by_id(event.id)

    @pytest.mark.asyncio
    async def test_update_event_not_found(self, event_repository):
        event = _make_event()

        with pytest.raises(EventNotFoundError):
            await event_repository.update_event(event)

    @pytest.mark.asyncio
    async def test_delete_event_not_found(self, event_repository):
        with pytest.raises(EventNotFoundError):
            await event_repository.delete_event(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_get_events_page_by_num(self, event_repository):
        events = [_make_event() for _ in range(5)]
        for event in events:
            await event_repository.create_event(event)

        page = await event_repository.get_events_page_by_num(offset=0, limit=3)

        assert len(page) == 3

    @pytest.mark.asyncio
    async def test_get_events_page_by_num_with_offset(self, event_repository):
        events = [_make_event() for _ in range(5)]
        for event in events:
            await event_repository.create_event(event)

        first_page = await event_repository.get_events_page_by_num(offset=0, limit=2)
        second_page = await event_repository.get_events_page_by_num(offset=2, limit=2)

        assert len(first_page) == 2
        assert len(second_page) == 2
        assert first_page[0].id != second_page[0].id

    @pytest.mark.asyncio
    async def test_get_events_page_by_num_empty(self, event_repository):
        page = await event_repository.get_events_page_by_num(offset=0, limit=10)
        assert page == []

    @pytest.mark.asyncio
    async def test_get_events_page_by_id(self, event_repository):
        events = [_make_event() for _ in range(5)]
        for event in events:
            await event_repository.create_event(event)

        first_event = events[0]
        page = await event_repository.get_events_page_by_id(
            event_id=first_event.id, limit=10
        )

        assert len(page) == 4

    @pytest.mark.asyncio
    async def test_get_events_page_by_id_limit(self, event_repository):
        events = [_make_event() for _ in range(5)]
        for event in events:
            await event_repository.create_event(event)

        first_event = events[0]
        page = await event_repository.get_events_page_by_id(
            event_id=first_event.id, limit=2
        )

        assert len(page) == 2

    @pytest.mark.asyncio
    async def test_get_events_page_by_id_empty(self, event_repository):
        page = await event_repository.get_events_page_by_id(
            event_id=uuid.uuid4(), limit=10
        )
        assert page == []
