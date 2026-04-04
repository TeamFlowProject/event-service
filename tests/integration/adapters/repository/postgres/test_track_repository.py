import uuid
from datetime import datetime, timezone

import psycopg_pool
import pytest
import pytest_asyncio
from testcontainers.postgres import PostgresContainer

from migrations.migrate import up
from src.adapters.repository.errors import TrackNotFoundError
from src.adapters.repository.postgres.track_repository import TrackPostgresRepository
from src.models.track import Role, Track, TrackStatusEnum


@pytest.fixture(scope="module")
def postgres_container():
    with PostgresContainer("postgres:17") as pg:
        host = pg.get_container_host_ip()
        port = pg.get_exposed_port(5432)
        user = pg.username
        password = pg.password
        dbname = pg.dbname
        dsn = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        yoyo_dsn = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{dbname}"
        up(yoyo_dsn)
        yield dsn


@pytest_asyncio.fixture
async def pool(postgres_container):
    async with psycopg_pool.AsyncConnectionPool(
        conninfo=postgres_container,
        min_size=1,
        max_size=2,
    ) as pool:
        yield pool


@pytest_asyncio.fixture
async def repository(pool):
    return TrackPostgresRepository(pool)


@pytest_asyncio.fixture
async def event_id(pool):
    eid = uuid.uuid4()
    async with pool.connection() as conn:
        await conn.execute(
            "INSERT INTO events (id) VALUES (%s)", (str(eid),)
        )
    return eid


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
    async def test_create_and_get_track(self, repository, event_id):
        track = _make_track(event_id)

        await repository.create_track(track)
        result = await repository.get_track(track.id)

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
    async def test_get_track_not_found(self, repository):
        with pytest.raises(TrackNotFoundError):
            await repository.get_track(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_update_track(self, repository, event_id):
        track = _make_track(event_id)
        await repository.create_track(track)

        track.name = "Updated Track"
        track.status = TrackStatusEnum.OPEN
        track.required_roles = [track.required_roles[0]]

        await repository.update_track(track)
        result = await repository.get_track(track.id)

        assert result.name == "Updated Track"
        assert result.status == TrackStatusEnum.OPEN
        assert len(result.required_roles) == 1
        assert result.required_roles[0].name == "Developer"

    @pytest.mark.asyncio
    async def test_delete_track(self, repository, event_id):
        track = _make_track(event_id)
        await repository.create_track(track)

        await repository.delete_track(track.id)

        with pytest.raises(TrackNotFoundError):
            await repository.get_track(track.id)

    @pytest.mark.asyncio
    async def test_update_track_not_found(self, repository, event_id):
        track = _make_track(event_id)

        with pytest.raises(TrackNotFoundError):
            await repository.update_track(track)

    @pytest.mark.asyncio
    async def test_delete_track_not_found(self, repository):
        with pytest.raises(TrackNotFoundError):
            await repository.delete_track(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_get_tracks_by_event_id(self, repository, event_id):
        track1 = _make_track(event_id)
        track2 = _make_track(event_id)
        track2.name = "Frontend Track"

        await repository.create_track(track1)
        await repository.create_track(track2)

        results = await repository.get_tracks_by_event_id(event_id)

        assert len(results) == 2
        names = {t.name for t in results}
        assert names == {"Backend Track", "Frontend Track"}

        for t in results:
            assert len(t.required_roles) == 2

    @pytest.mark.asyncio
    async def test_get_tracks_by_event_id_empty(self, repository):
        results = await repository.get_tracks_by_event_id(uuid.uuid4())
        assert results == []
