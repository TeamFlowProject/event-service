import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from uuid_extensions import uuid7

from src.adapters.repository.errors import TrackNotFoundError
from src.adapters.repository.event.postgres.repository import EventPostgresRepository
from src.models.event import Event, EventTypeEnum, EventStatusEnum
from src.models.track import Role, Track, TrackStatusEnum


@pytest_asyncio.fixture
async def event_id(pool):
    event = Event(
        id=uuid.uuid4(),
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


def _make_track(event_id: uuid.UUID) -> Track:
    track_id = uuid.uuid4()
    return Track(
        id=track_id,
        event_id=event_id,
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
            Role(
                id=uuid.uuid4(),
                track_id=track_id,
                name="Designer",
                description="UI/UX designer",
                count=1,
            ),
        ],
        requirements="Python experience",
        status=TrackStatusEnum.DRAFT,
        registration_deadline=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )


@pytest.mark.integration
@pytest.mark.usefixtures("cleanup")
class TestTrackPostgresRepository:
    @pytest.mark.asyncio
    async def test_create_and_get_track(self, track_repository, event_id):
        track = _make_track(event_id)

        await track_repository.create_track(track)
        result = await track_repository.get_track(track.id)

        assert result.id == track.id
        assert result.event_id == event_id
        assert result.name == track.name
        assert result.description == track.description
        assert result.max_team_count == track.max_team_count
        assert result.status == TrackStatusEnum.DRAFT
        assert len(result.required_roles) == 2

        role_names = {r.name for r in result.required_roles}
        assert role_names == {"Developer", "Designer"}

    @pytest.mark.asyncio
    async def test_get_track_not_found(self, track_repository):
        with pytest.raises(TrackNotFoundError):
            await track_repository.get_track(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_update_track(self, track_repository, event_id):
        track = _make_track(event_id)
        await track_repository.create_track(track)

        track.name = "Updated Track"
        track.status = TrackStatusEnum.OPEN
        track.required_roles = [track.required_roles[0]]

        await track_repository.update_track(track)
        result = await track_repository.get_track(track.id)

        assert result.name == "Updated Track"
        assert result.status == TrackStatusEnum.OPEN
        assert len(result.required_roles) == 1
        assert result.required_roles[0].name == "Developer"

    @pytest.mark.asyncio
    async def test_delete_track(self, track_repository, event_id):
        track = _make_track(event_id)
        await track_repository.create_track(track)

        await track_repository.delete_track(track.id)

        with pytest.raises(TrackNotFoundError):
            await track_repository.get_track(track.id)

    @pytest.mark.asyncio
    async def test_update_track_not_found(self, track_repository, event_id):
        track = _make_track(event_id)

        with pytest.raises(TrackNotFoundError):
            await track_repository.update_track(track)

    @pytest.mark.asyncio
    async def test_delete_track_not_found(self, track_repository):
        with pytest.raises(TrackNotFoundError):
            await track_repository.delete_track(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_get_tracks_by_event_id(self, track_repository, event_id):
        track1 = _make_track(event_id)
        track2 = _make_track(event_id)
        track2.name = "Frontend Track"

        await track_repository.create_track(track1)
        await track_repository.create_track(track2)

        results = await track_repository.get_tracks_by_event_id(event_id)

        assert len(results) == 2
        names = {t.name for t in results}
        assert names == {"Backend Track", "Frontend Track"}

        for t in results:
            assert len(t.required_roles) == 2

    @pytest.mark.asyncio
    async def test_get_tracks_by_event_id_empty(self, track_repository):
        results = await track_repository.get_tracks_by_event_id(uuid.uuid4())
        assert results == []
