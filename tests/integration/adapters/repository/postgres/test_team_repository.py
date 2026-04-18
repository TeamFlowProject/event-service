import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from src.adapters.repository.errors import (
    TeamAlreadyExistsError,
    TeamNotFoundError,
    ParticipantNotFoundError,
)
from src.adapters.repository.event.postgres.repository import EventPostgresRepository
from src.adapters.repository.team.postgres.repository import TeamPostgresRepository
from src.adapters.repository.track.postgres.repository import TrackPostgresRepository
from src.models.event import Event, EventTypeEnum, EventStatusEnum, Participant
from src.models.team import Team, TeamStatusEnum
from src.models.track import Role, Track, TrackStatusEnum


@pytest_asyncio.fixture
async def cleanup(pool):
    yield
    async with pool.connection() as conn:
        await conn.execute("DELETE FROM team_members")
        await conn.execute("DELETE FROM team_roles")
        await conn.execute("DELETE FROM teams")
        await conn.execute("DELETE FROM event_participants")
        await conn.execute("DELETE FROM participants")
        await conn.execute("DELETE FROM roles")
        await conn.execute("DELETE FROM tracks")
        await conn.execute("DELETE FROM events")


@pytest_asyncio.fixture
async def team_repository(pool):
    return TeamPostgresRepository(pool)


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
        rules="Rules",
        faq="FAQ",
        status=EventStatusEnum.OPEN,
    )
    await EventPostgresRepository(pool).create_event(event)
    return event.id


@pytest_asyncio.fixture
async def track(pool, event_id):
    track_id = uuid.uuid4()
    t = Track(
        id=track_id,
        event_id=event_id,
        name="Backend Track",
        description="Backend track",
        max_team_count=10,
        max_participants_count=50,
        min_team_size=2,
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
                description="UI/UX Designer",
                count=1,
            ),
        ],
        requirements="Python",
        status=TrackStatusEnum.OPEN,
        registration_deadline=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    await TrackPostgresRepository(pool).create_track(t)
    return t


@pytest_asyncio.fixture
async def owner(pool, event_id, track):
    participant = Participant(
        id=uuid.uuid4(),
        event_id=event_id,
        name="Alice",
        surname="Smith",
        patronymic="Doe",
        have_team=False,
        role_id=track.required_roles[0].id,
    )
    await EventPostgresRepository(pool).add_participant(event_id, participant)
    return participant


@pytest_asyncio.fixture
async def member(pool, event_id, track):
    participant = Participant(
        id=uuid.uuid4(),
        event_id=event_id,
        name="Bob",
        surname="Jones",
        patronymic="Lee",
        have_team=False,
        role_id=track.required_roles[1].id,
    )
    await EventPostgresRepository(pool).add_participant(event_id, participant)
    return participant


def _make_team(event_id: uuid.UUID, track: Track, owner: Participant) -> Team:
    return Team(
        id=uuid.uuid4(),
        track_id=track.id,
        event_id=event_id,
        owner=owner,
        members=[],
        required_roles=[],
        name="Test Team",
        description="Test Description",
        status=TeamStatusEnum.DRAFT,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


async def _insert_member_into_team(
    pool, team_id: uuid.UUID, participant: Participant
) -> None:
    async with pool.connection() as conn:
        await conn.execute(
            "INSERT INTO team_members (team_id, member_id, role_id) VALUES (%s, %s, %s)",
            (str(team_id), str(participant.id), str(participant.role_id)),
        )


async def _set_have_team(
    pool, participant_id: uuid.UUID, event_id: uuid.UUID, value: bool
) -> None:
    async with pool.connection() as conn:
        await conn.execute(
            "UPDATE event_participants SET have_team = %s"
            " WHERE participant_id = %s AND event_id = %s",
            (value, str(participant_id), str(event_id)),
        )


@pytest.mark.integration
@pytest.mark.usefixtures("cleanup")
class TestTeamPostgresRepository:

    @pytest.mark.asyncio
    async def test_create_and_get_team(
        self, team_repository, event_id, track, owner
    ):
        team = _make_team(event_id, track, owner)
        await team_repository.create_team(team)

        result = await team_repository.get_team(team.id)

        assert result.id == team.id
        assert result.track_id == track.id
        assert result.event_id == event_id
        assert result.owner.id == owner.id
        assert result.name == team.name
        assert result.description == team.description
        assert result.status == TeamStatusEnum.DRAFT
        assert result.members == []

    @pytest.mark.asyncio
    async def test_create_team_populates_roles_from_track(
        self, team_repository, event_id, track, owner
    ):
        team = _make_team(event_id, track, owner)
        await team_repository.create_team(team)

        result = await team_repository.get_team(team.id)

        assert len(result.required_roles) == 2
        role_names = {r.name for r in result.required_roles}
        assert role_names == {"Developer", "Designer"}

    @pytest.mark.asyncio
    async def test_create_team_owner_role_decrements_required_count(
        self, team_repository, event_id, track, owner
    ):
        team = _make_team(event_id, track, owner)
        await team_repository.create_team(team)

        result = await team_repository.get_team(team.id)

        developer = next(r for r in result.required_roles if r.name == "Developer")
        designer = next(r for r in result.required_roles if r.name == "Designer")

        assert developer.count == 2
        assert designer.count == 1

    @pytest.mark.asyncio
    async def test_create_team_sets_owner_have_team(
        self, team_repository, event_id, track, owner
    ):
        team = _make_team(event_id, track, owner)
        await team_repository.create_team(team)

        fetched_owner = await team_repository.get_member_by_id(owner.id, event_id)
        assert fetched_owner.have_team is True

    @pytest.mark.asyncio
    async def test_create_team_without_owner_role_does_not_decrement(
        self, team_repository, event_id, track, pool
    ):
        owner_no_role = Participant(
            id=uuid.uuid4(),
            event_id=event_id,
            name="Carol",
            surname="White",
            patronymic="Ann",
            have_team=False,
            role_id=None,
        )
        await EventPostgresRepository(pool).add_participant(event_id, owner_no_role)

        team = _make_team(event_id, track, owner_no_role)
        await team_repository.create_team(team)

        result = await team_repository.get_team(team.id)

        developer = next(r for r in result.required_roles if r.name == "Developer")
        designer = next(r for r in result.required_roles if r.name == "Designer")

        assert developer.count == 3
        assert designer.count == 1

    @pytest.mark.asyncio
    async def test_create_team_duplicate_raises(
        self, team_repository, event_id, track, owner
    ):
        team = _make_team(event_id, track, owner)
        await team_repository.create_team(team)

        with pytest.raises(TeamAlreadyExistsError):
            await team_repository.create_team(team)

    @pytest.mark.asyncio
    async def test_create_team_owner_not_in_members(
        self, team_repository, event_id, track, owner
    ):
        team = _make_team(event_id, track, owner)
        await team_repository.create_team(team)

        result = await team_repository.get_team(team.id)

        member_ids = {m.id for m in result.members}
        assert owner.id not in member_ids

    @pytest.mark.asyncio
    async def test_get_team_not_found(self, team_repository):
        with pytest.raises(TeamNotFoundError):
            await team_repository.get_team(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_get_member_by_id(self, team_repository, event_id, owner):
        result = await team_repository.get_member_by_id(owner.id, event_id)

        assert result.id == owner.id
        assert result.event_id == event_id
        assert result.name == owner.name
        assert result.surname == owner.surname
        assert result.have_team is False

    @pytest.mark.asyncio
    async def test_get_member_by_id_not_found(self, team_repository, event_id):
        with pytest.raises(ParticipantNotFoundError):
            await team_repository.get_member_by_id(uuid.uuid4(), event_id)

    @pytest.mark.asyncio
    async def test_get_member_by_id_wrong_event(
        self, team_repository, owner
    ):
        with pytest.raises(ParticipantNotFoundError):
            await team_repository.get_member_by_id(owner.id, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_remove_member_increments_required_count(
        self, team_repository, event_id, track, owner, member, pool
    ):
        team = _make_team(event_id, track, owner)
        await team_repository.create_team(team)

        await _insert_member_into_team(pool, team.id, member)
        await _set_have_team(pool, member.id, event_id, True)

        async with pool.connection() as conn:
            await conn.execute(
                "UPDATE team_roles SET required_count = required_count - 1"
                " WHERE team_id = %s AND role_id = %s",
                (str(team.id), str(member.role_id)),
            )

        await team_repository.remove_member(team.id, member.id)

        result = await team_repository.get_team(team.id)
        designer = next(r for r in result.required_roles if r.name == "Designer")
        assert designer.count == 1

    @pytest.mark.asyncio
    async def test_remove_member_sets_have_team_false(
        self, team_repository, event_id, track, owner, member, pool
    ):
        team = _make_team(event_id, track, owner)
        await team_repository.create_team(team)

        await _insert_member_into_team(pool, team.id, member)
        await _set_have_team(pool, member.id, event_id, True)

        await team_repository.remove_member(team.id, member.id)

        fetched = await team_repository.get_member_by_id(member.id, event_id)
        assert fetched.have_team is False

    @pytest.mark.asyncio
    async def test_remove_member_not_in_team_raises(
        self, team_repository, event_id, track, owner, member
    ):
        team = _make_team(event_id, track, owner)
        await team_repository.create_team(team)

        with pytest.raises(TeamNotFoundError):
            await team_repository.remove_member(team.id, member.id)

    @pytest.mark.asyncio
    async def test_remove_member_team_not_found_raises(
        self, team_repository, member
    ):
        with pytest.raises(TeamNotFoundError):
            await team_repository.remove_member(uuid.uuid4(), member.id)

    @pytest.mark.asyncio
    async def test_remove_member_not_in_members_after_remove(
        self, team_repository, event_id, track, owner, member, pool
    ):
        team = _make_team(event_id, track, owner)
        await team_repository.create_team(team)
        await _insert_member_into_team(pool, team.id, member)

        await team_repository.remove_member(team.id, member.id)

        result = await team_repository.get_team(team.id)
        member_ids = {m.id for m in result.members}
        assert member.id not in member_ids

    @pytest.mark.asyncio
    async def test_delete_team(self, team_repository, event_id, track, owner):
        team = _make_team(event_id, track, owner)
        await team_repository.create_team(team)

        await team_repository.delete_team(team.id)

        with pytest.raises(TeamNotFoundError):
            await team_repository.get_team(team.id)

    @pytest.mark.asyncio
    async def test_delete_team_resets_owner_have_team(
        self, team_repository, event_id, track, owner
    ):
        team = _make_team(event_id, track, owner)
        await team_repository.create_team(team)

        fetched_before = await team_repository.get_member_by_id(owner.id, event_id)
        assert fetched_before.have_team is True

        await team_repository.delete_team(team.id)

        fetched_after = await team_repository.get_member_by_id(owner.id, event_id)
        assert fetched_after.have_team is False

    @pytest.mark.asyncio
    async def test_delete_team_resets_members_have_team(
        self, team_repository, event_id, track, owner, member, pool
    ):
        team = _make_team(event_id, track, owner)
        await team_repository.create_team(team)
        await _insert_member_into_team(pool, team.id, member)
        await _set_have_team(pool, member.id, event_id, True)

        await team_repository.delete_team(team.id)

        fetched = await team_repository.get_member_by_id(member.id, event_id)
        assert fetched.have_team is False

    @pytest.mark.asyncio
    async def test_delete_team_not_found_raises(self, team_repository):
        with pytest.raises(TeamNotFoundError):
            await team_repository.delete_team(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_update_team(self, team_repository, event_id, track, owner):
        team = _make_team(event_id, track, owner)
        await team_repository.create_team(team)

        team.name = "Updated Name"
        team.description = "Updated Description"
        team.status = TeamStatusEnum.BUILDING

        await team_repository.update_team(team)

        result = await team_repository.get_team(team.id)
        assert result.name == "Updated Name"
        assert result.description == "Updated Description"
        assert result.status == TeamStatusEnum.BUILDING

    @pytest.mark.asyncio
    async def test_update_team_does_not_change_roles(
        self, team_repository, event_id, track, owner
    ):
        team = _make_team(event_id, track, owner)
        await team_repository.create_team(team)

        before = await team_repository.get_team(team.id)
        before_counts = {r.name: r.count for r in before.required_roles}

        team.name = "Renamed"
        await team_repository.update_team(team)

        after = await team_repository.get_team(team.id)
        after_counts = {r.name: r.count for r in after.required_roles}

        assert before_counts == after_counts

    @pytest.mark.asyncio
    async def test_update_team_not_found_raises(
        self, team_repository, event_id, track, owner
    ):
        team = _make_team(event_id, track, owner)

        with pytest.raises(TeamNotFoundError):
            await team_repository.update_team(team)

    @pytest.mark.asyncio
    async def test_change_team_status(
        self, team_repository, event_id, track, owner
    ):
        team = _make_team(event_id, track, owner)
        await team_repository.create_team(team)

        await team_repository.change_team_status(team.id, TeamStatusEnum.FULL)

        result = await team_repository.get_team(team.id)
        assert result.status == TeamStatusEnum.FULL

    @pytest.mark.asyncio
    async def test_change_team_status_not_found_raises(self, team_repository):
        with pytest.raises(TeamNotFoundError):
            await team_repository.change_team_status(
                uuid.uuid4(), TeamStatusEnum.FULL
            )

    @pytest.mark.asyncio
    async def test_get_team_includes_members(
        self, team_repository, event_id, track, owner, member, pool
    ):
        team = _make_team(event_id, track, owner)
        await team_repository.create_team(team)
        await _insert_member_into_team(pool, team.id, member)

        result = await team_repository.get_team(team.id)

        member_ids = {m.id for m in result.members}
        assert member.id in member_ids
        assert owner.id not in member_ids

    @pytest.mark.asyncio
    async def test_get_team_member_has_role_id(
        self, team_repository, event_id, track, owner, member, pool
    ):
        team = _make_team(event_id, track, owner)
        await team_repository.create_team(team)
        await _insert_member_into_team(pool, team.id, member)

        result = await team_repository.get_team(team.id)

        fetched_member = next(m for m in result.members if m.id == member.id)
        assert fetched_member.role_id == member.role_id
