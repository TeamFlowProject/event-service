import uuid
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

import src.adapters.repository.errors as adapter_errors
import src.service.errors as service_errors
from src.models.track import Track, TrackStatusEnum
from src.service.track.service import TrackService


def make_track(**kwargs) -> Track:
    defaults = dict(
        id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        name="Test Track",
        description="A test track",
        max_team_count=10,
        max_participants_count=100,
        min_team_size=1,
        max_team_size=5,
        required_roles=[],
        requirements="None",
        status=TrackStatusEnum.DRAFT,
        registration_deadline=datetime(2026, 6, 1),
    )
    defaults.update(kwargs)
    return Track(**defaults)  # type: ignore


@pytest.fixture
def repo():
    return AsyncMock()


@pytest.fixture
def kafka():
    return AsyncMock()


@pytest.fixture
def service(repo, kafka):
    return TrackService(track_repository=repo, kafka_producer=kafka)


@pytest.mark.unit
class TestCreateTrack:
    @pytest.mark.asyncio
    async def test_returns_id(self, service):
        track = make_track()

        result = await service.create_track(track)

        assert isinstance(result, uuid.UUID)

    @pytest.mark.asyncio
    async def test_calls_repo_and_kafka(self, service, repo, kafka):
        track = make_track()

        await service.create_track(track)

        repo.create_track.assert_called_once_with(track)
        kafka.send_create_track.assert_called_once_with(track)

    @pytest.mark.asyncio
    async def test_raises_event_not_found(self, service, repo):
        repo.create_track.side_effect = adapter_errors.EventNotFoundError

        with pytest.raises(service_errors.EventNotFoundError):
            await service.create_track(make_track())

    @pytest.mark.asyncio
    async def test_does_not_call_kafka_when_event_not_found(self, service, repo, kafka):
        repo.create_track.side_effect = adapter_errors.EventNotFoundError

        with pytest.raises(service_errors.EventNotFoundError):
            await service.create_track(make_track())

        kafka.send_create_track.assert_not_called()


@pytest.mark.unit
class TestUpdateTrack:
    @pytest.mark.asyncio
    async def test_calls_repo_and_kafka(self, service, repo, kafka):
        track = make_track()

        await service.update_track(track)

        repo.update_track.assert_called_once_with(track)
        kafka.send_update_track.assert_called_once_with(track)

    @pytest.mark.asyncio
    async def test_raises_service_error_when_not_found(self, service, repo, kafka):
        repo.update_track.side_effect = adapter_errors.TrackNotFoundError

        with pytest.raises(service_errors.TrackNotFoundError):
            await service.update_track(make_track())

        kafka.send_update_track.assert_not_called()


@pytest.mark.unit
class TestDeleteTrack:
    @pytest.mark.asyncio
    async def test_calls_repo_and_kafka(self, service, repo, kafka):
        track = make_track()
        repo.get_track.return_value = track

        await service.delete_track(track.id)

        repo.get_track.assert_called_once_with(track.id)
        repo.delete_track.assert_called_once_with(track.id)
        kafka.send_delete_track.assert_called_once_with(track)

    @pytest.mark.asyncio
    async def test_raises_service_error_when_not_found(self, service, repo, kafka):
        repo.get_track.side_effect = adapter_errors.TrackNotFoundError

        with pytest.raises(service_errors.TrackNotFoundError):
            await service.delete_track(uuid.uuid4())

        kafka.send_delete_track.assert_not_called()


@pytest.mark.unit
class TestGetTrack:
    @pytest.mark.asyncio
    async def test_returns_track(self, service, repo):
        track = make_track()
        repo.get_track.return_value = track

        result = await service.get_track(track.id)

        assert result == track
        repo.get_track.assert_called_once_with(track.id)

    @pytest.mark.asyncio
    async def test_raises_track_not_found(self, service, repo):
        repo.get_track.side_effect = adapter_errors.TrackNotFoundError

        with pytest.raises(service_errors.TrackNotFoundError):
            await service.get_track(uuid.uuid4())


@pytest.mark.unit
class TestGetTracksByEventId:
    @pytest.mark.asyncio
    async def test_returns_tracks(self, service, repo):
        event_id = uuid.uuid4()
        tracks = [make_track(event_id=event_id), make_track(event_id=event_id)]
        repo.get_tracks_by_event_id.return_value = tracks

        result = await service.get_tracks_by_event_id(event_id)

        assert result == tracks
        repo.get_tracks_by_event_id.assert_called_once_with(event_id)

    @pytest.mark.asyncio
    async def test_returns_empty_list_for_unknown_event(self, service, repo):
        repo.get_tracks_by_event_id.return_value = []

        result = await service.get_tracks_by_event_id(uuid.uuid4())

        assert result == []
