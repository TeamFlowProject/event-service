import uuid
from datetime import datetime
from unittest.mock import MagicMock
import pytest

import src.adapters.repository.errors as adapter_errors
import src.service.errors as service_errors
from src.models.track import Track, Role, TrackStatusEnum
from src.service.track_service import TrackService


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
    return MagicMock()


@pytest.fixture
def kafka():
    return MagicMock()


@pytest.fixture
def service(repo, kafka):
    return TrackService(track_repository=repo, kafka_producer=kafka)


class TestCreateTrack:
    def test_returns_id(self, service, repo, kafka):
        track = make_track()
        new_id = uuid.uuid4()
        repo.create_track.return_value = new_id

        result = service.create_track(track)

        assert result == new_id

    def test_sets_track_id_before_kafka(self, service, repo, kafka):
        track = make_track()
        new_id = uuid.uuid4()
        repo.create_track.return_value = new_id

        service.create_track(track)

        sent_track = kafka.send_create_track.call_args[0][0]
        assert sent_track.id == new_id

    def test_calls_repo_and_kafka(self, service, repo, kafka):
        track = make_track()
        repo.create_track.return_value = uuid.uuid4()

        service.create_track(track)

        repo.create_track.assert_called_once_with(track)
        kafka.send_create_track.assert_called_once()


class TestUpdateTrack:
    def test_calls_repo_and_kafka(self, service, repo, kafka):
        track = make_track()

        service.update_track(track)

        repo.update_track.assert_called_once_with(track)
        kafka.send_update_track.assert_called_once_with(track)

    def test_raises_service_error_when_not_found(self, service, repo, kafka):
        repo.update_track.side_effect = adapter_errors.TrackNotFoundError

        with pytest.raises(service_errors.TrackNotFoundError):
            service.update_track(make_track())

        kafka.send_update_track.assert_not_called()


class TestDeleteTrack:
    def test_calls_repo_and_kafka(self, service, repo, kafka):
        track_id = uuid.uuid4()

        service.delete_track(track_id)

        repo.delete_track.assert_called_once_with(track_id)
        kafka.send_delete_track.assert_called_once_with(track_id)

    def test_raises_service_error_when_not_found(self, service, repo, kafka):
        repo.delete_track.side_effect = adapter_errors.TrackNotFoundError

        with pytest.raises(service_errors.TrackNotFoundError):
            service.delete_track(uuid.uuid4())

        kafka.send_delete_track.assert_not_called()


class TestGetTrack:
    def test_returns_track(self, service, repo):
        track = make_track()
        repo.get_track.return_value = track

        result = service.get_track(track.id)

        assert result == track
        repo.get_track.assert_called_once_with(track.id)

    def test_raises_track_not_found(self, service, repo):
        repo.get_track.side_effect = adapter_errors.TrackNotFoundError

        with pytest.raises(service_errors.TrackNotFoundError):
            service.get_track(uuid.uuid4())

    def test_raises_role_not_found(self, service, repo):
        repo.get_track.side_effect = adapter_errors.RoleNotFoundError

        with pytest.raises(service_errors.RoleNotFoundError):
            service.get_track(uuid.uuid4())


class TestGetTracksByEventId:
    def test_returns_tracks(self, service, repo):
        event_id = uuid.uuid4()
        tracks = [make_track(event_id=event_id), make_track(event_id=event_id)]
        repo.get_tracks_by_event_id.return_value = tracks

        result = service.get_tracks_by_event_id(event_id)

        assert result == tracks
        repo.get_tracks_by_event_id.assert_called_once_with(event_id)

    def test_raises_event_not_found(self, service, repo):
        repo.get_tracks_by_event_id.side_effect = adapter_errors.EventNotFoundError

        with pytest.raises(service_errors.EventNotFoundError):
            service.get_tracks_by_event_id(uuid.uuid4())

    def test_raises_role_not_found(self, service, repo):
        repo.get_tracks_by_event_id.side_effect = adapter_errors.RoleNotFoundError

        with pytest.raises(service_errors.RoleNotFoundError):
            service.get_tracks_by_event_id(uuid.uuid4())
