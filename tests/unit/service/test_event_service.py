import uuid
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from typing import cast
from uuid_extensions import uuid7

import src.adapters.repository.errors as adapter_errors
import src.service.errors as service_errors
from src.models.event import Event, Participant, EventStatusEnum, EventTypeEnum
from src.service.event.service import EventService


def make_event(**kwargs) -> Event:
    defaults = dict(
        id=cast(uuid.UUID, uuid7()),
        name="Test Event",
        description="A test event",
        type=EventTypeEnum.HACKATHON,
        registration_start=datetime(2026, 5, 1, 0, 0),
        registration_end=datetime(2026, 6, 10, 23, 59),
        holding_start=datetime(2026, 6, 15, 10, 0),
        holding_end=datetime(2026, 6, 17, 18, 0),
        created_at=datetime.now(),
        organizers=["Organizer 1", "Organizer 2"],
        rules="No cheating",
        faq="faq content",
        status=EventStatusEnum.DRAFT,
    )
    defaults.update(kwargs)
    return Event(**defaults)  # type: ignore


def make_participant(**kwargs) -> Participant:
    defaults = dict(
        id=cast(uuid.UUID, uuid7()),
        event_id=cast(uuid.UUID, uuid7()),
        name="John",
        surname="Doe",
        patronymic="Johnovich",
        have_team=False,
    )
    defaults.update(kwargs)
    return Participant(**defaults)  # type: ignore


@pytest.fixture
def repo():
    return AsyncMock()


@pytest.fixture
def kafka():
    return AsyncMock()


@pytest.fixture
def service(repo, kafka):
    return EventService(event_repository=repo, kafka_producer=kafka)


@pytest.mark.unit
class TestGetEventById:
    @pytest.mark.asyncio
    async def test_returns_event(self, service, repo):
        event = make_event()
        repo.get_event_by_id.return_value = event

        result = await service.get_event_by_id(event.id)

        assert result == event
        repo.get_event_by_id.assert_called_once_with(event.id)

    @pytest.mark.asyncio
    async def test_raises_event_not_found(self, service, repo):
        repo.get_event_by_id.side_effect = adapter_errors.EventNotFoundError

        with pytest.raises(service_errors.EventNotFoundError):
            await service.get_event_by_id(cast(uuid.UUID, uuid7()))


@pytest.mark.unit
class TestGetEventsPage:
    @pytest.mark.asyncio
    async def test_returns_events_by_id(self, service, repo):
        event = make_event()
        repo.get_events_page_by_id.return_value = [event]
        event_id = cast(uuid.UUID, uuid7())

        result = await service.get_events_page(event_id=event_id, limit=10)

        assert result == [event]
        repo.get_events_page_by_id.assert_called_once_with(event_id=event_id, limit=10)

    @pytest.mark.asyncio
    async def test_returns_events_by_offset(self, service, repo):
        events = [make_event(), make_event()]
        repo.get_events_page_by_num.return_value = events
        offset = 0

        result = await service.get_events_page(offset=offset, limit=10)

        assert result == events
        repo.get_events_page_by_num.assert_called_once_with(offset=offset, limit=10)

    @pytest.mark.asyncio
    async def test_raises_error_when_both_none(self, service):
        with pytest.raises(service_errors.PaginationError):
            await service.get_events_page(event_id=None, offset=None)

    @pytest.mark.asyncio
    async def test_raises_error_when_both_specified(self, service):
        with pytest.raises(service_errors.PaginationError):
            await service.get_events_page(event_id=cast(uuid.UUID, uuid7()), offset=0)


@pytest.mark.unit
class TestCreateEvent:
    @pytest.mark.asyncio
    async def test_returns_id(self, service):
        event = make_event()

        result = await service.create_event(event)

        assert isinstance(result, uuid.UUID)

    @pytest.mark.asyncio
    async def test_calls_repo_and_kafka(self, service, repo, kafka):
        event = make_event()

        await service.create_event(event)

        repo.create_event.assert_called_once_with(event)
        kafka.send_create_event.assert_called_once()


@pytest.mark.unit
class TestUpdateEvent:
    @pytest.mark.asyncio
    async def test_calls_repo_and_kafka(self, service, repo, kafka):
        event = make_event()

        await service.update_event(event)

        repo.update_event.assert_called_once_with(event)
        kafka.send_update_event.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_raises_service_error_when_not_found(self, service, repo, kafka):
        repo.update_event.side_effect = adapter_errors.EventNotFoundError

        with pytest.raises(service_errors.EventNotFoundError):
            await service.update_event(make_event())

        kafka.send_update_event.assert_not_called()


@pytest.mark.unit
class TestDeleteEvent:
    @pytest.mark.asyncio
    async def test_calls_repo_and_kafka(self, service, repo, kafka):
        event_id = cast(uuid.UUID, uuid7())
        mock_event = make_event(id=event_id)
        repo.get_event_by_id.return_value = mock_event

        await service.delete_event(event_id)

        repo.get_event_by_id.assert_called_once_with(event_id)
        repo.delete_event.assert_called_once_with(event_id)
        kafka.send_delete_event.assert_called_once_with(mock_event)

    @pytest.mark.asyncio
    async def test_raises_service_error_when_not_found(self, service, repo, kafka):
        repo.get_event_by_id.side_effect = adapter_errors.EventNotFoundError

        with pytest.raises(service_errors.EventNotFoundError):
            await service.delete_event(cast(uuid.UUID, uuid7()))

        repo.delete_event.assert_not_called()
        kafka.send_delete_event.assert_not_called()


@pytest.mark.unit
class TestAddParticipant:
    @pytest.mark.asyncio
    async def test_adds_participant_when_event_open(self, service, repo, kafka):
        event = make_event(status=EventStatusEnum.OPEN)
        participant = make_participant()
        repo.get_event_by_id.return_value = event

        await service.add_participant(event.id, participant)

        repo.add_participant.assert_called_once_with(event.id, participant)
        kafka.send_participant.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_error_when_event_not_open(self, service, repo, kafka):
        event = make_event(status=EventStatusEnum.CLOSED)
        participant = make_participant()
        repo.get_event_by_id.return_value = event

        with pytest.raises(service_errors.ParticipantError):
            await service.add_participant(event.id, participant)

        repo.add_participant.assert_not_called()
        kafka.send_participant.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_error_when_event_not_found(self, service, repo):
        participant = make_participant()
        repo.get_event_by_id.side_effect = adapter_errors.EventNotFoundError

        with pytest.raises(service_errors.EventNotFoundError):
            await service.add_participant(cast(uuid.UUID, uuid7()), participant)

        repo.add_participant.assert_not_called()


@pytest.mark.unit
class TestGetParticipants:
    @pytest.mark.asyncio
    async def test_returns_participants_by_id(self, service, repo):
        event_id = cast(uuid.UUID, uuid7())
        participant = make_participant(event_id=event_id)
        repo.get_participants_by_id.return_value = [participant]
        participant_id = cast(uuid.UUID, uuid7())

        result = await service.get_participants(
            event_id=event_id, participant_id=participant_id, limit=10
        )

        assert result == [participant]
        repo.get_participants_by_id.assert_called_once_with(
            event_id, participant_id, 10
        )

    @pytest.mark.asyncio
    async def test_returns_participants_by_offset(self, service, repo):
        event_id = cast(uuid.UUID, uuid7())
        participants = [
            make_participant(event_id=event_id),
            make_participant(event_id=event_id),
        ]
        repo.get_participants_by_num.return_value = participants
        offset = 0

        result = await service.get_participants(
            event_id=event_id, offset=offset, limit=10
        )

        assert result == participants
        repo.get_participants_by_num.assert_called_once_with(event_id, offset, 10)

    @pytest.mark.asyncio
    async def test_raises_error_when_both_none(self, service):
        event_id = cast(uuid.UUID, uuid7())

        with pytest.raises(service_errors.PaginationError):
            await service.get_participants(
                event_id=event_id, participant_id=None, offset=None
            )

    @pytest.mark.asyncio
    async def test_raises_error_when_both_specified(self, service):
        event_id = cast(uuid.UUID, uuid7())

        with pytest.raises(service_errors.PaginationError):
            await service.get_participants(
                event_id=event_id, participant_id=cast(uuid.UUID, uuid7()), offset=0
            )

    @pytest.mark.asyncio
    async def test_raises_event_not_found(self, service, repo):
        repo.get_participants_by_id.side_effect = adapter_errors.EventNotFoundError

        with pytest.raises(service_errors.EventNotFoundError):
            await service.get_participants(
                event_id=cast(uuid.UUID, uuid7()), participant_id=uuid7()
            )

    @pytest.mark.asyncio
    async def test_raises_participant_not_found(self, service, repo):
        repo.get_participants_by_id.side_effect = (
            adapter_errors.ParticipantNotFoundError
        )

        with pytest.raises(service_errors.ParticipantNotFoundError):
            await service.get_participants(
                event_id=cast(uuid.UUID, uuid7()), participant_id=uuid7()
            )
