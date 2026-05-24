import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from src.adapters.repository.errors import (
    InvitationAlreadyExistsError,
    InvitationNotFoundError,
    JoinRequestAlreadyExistsError,
    JoinRequestNotFoundError,
    ParticipantAlreadyInTeamError,
    TeamNotFoundError,
)
from src.adapters.repository.event.postgres.repository import EventPostgresRepository
from src.adapters.repository.invitation.postgres.repository import (
    InvitationPostgresRepository,
)
from src.adapters.repository.team.postgres.repository import TeamPostgresRepository
from src.adapters.repository.track.postgres.repository import TrackPostgresRepository
from src.models.event import (
    Event,
    EventStatusEnum,
    EventTypeEnum,
    Participant,
)
from src.models.invitation import Invitation, JoinRequest
from src.models.team import Team, TeamStatusEnum
from src.models.track import Role, Track, TrackStatusEnum


@pytest_asyncio.fixture
async def cleanup(pool):
    yield
    async with pool.connection() as conn:
        await conn.execute("DELETE FROM invitations")
        await conn.execute("DELETE FROM join_requests")
        await conn.execute("DELETE FROM team_members")
        await conn.execute("DELETE FROM team_roles")
        await conn.execute("DELETE FROM teams")
        await conn.execute("DELETE FROM event_participants")
        await conn.execute("DELETE FROM participants")
        await conn.execute("DELETE FROM roles")
        await conn.execute("DELETE FROM tracks")
        await conn.execute("DELETE FROM events")


@pytest_asyncio.fixture
async def invitation_repository(pool):
    return InvitationPostgresRepository(pool)


@pytest_asyncio.fixture
async def event_id(pool):
    event = Event(
        id=uuid.uuid4(),
        name="Test Event",
        description="desc",
        type=EventTypeEnum.HACKATHON,
        registration_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
        registration_end=datetime(2025, 1, 10, tzinfo=timezone.utc),
        holding_start=datetime(2025, 1, 15, tzinfo=timezone.utc),
        holding_end=datetime(2025, 1, 17, tzinfo=timezone.utc),
        created_at=datetime.now(timezone.utc),
        organizers=["Organizer"],
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
        description="desc",
        max_team_count=10,
        max_participants_count=50,
        min_team_size=2,
        max_team_size=5,
        required_roles=[
            Role(
                id=uuid.uuid4(),
                track_id=track_id,
                name="Developer",
                description="Dev",
                count=3,
            ),
            Role(
                id=uuid.uuid4(),
                track_id=track_id,
                name="Designer",
                description="UI",
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
    p = Participant(
        id=uuid.uuid4(),
        event_id=event_id,
        name="Owner",
        surname="Surname",
        patronymic="Patronymic",
        have_team=False,
        role_id=track.required_roles[0].id,
    )
    await EventPostgresRepository(pool).add_participant(event_id, p)
    return p


@pytest_asyncio.fixture
async def member(pool, event_id, track):
    p = Participant(
        id=uuid.uuid4(),
        event_id=event_id,
        name="Member",
        surname="Surname",
        patronymic="Patronymic",
        have_team=False,
        role_id=track.required_roles[1].id,
    )
    await EventPostgresRepository(pool).add_participant(event_id, p)
    return p


@pytest_asyncio.fixture
async def team(pool, event_id, track, owner):
    t = Team(
        id=uuid.uuid4(),
        track_id=track.id,
        event_id=event_id,
        owner=owner,
        members=[],
        required_roles=[],
        name="Team A",
        description="desc",
        status=TeamStatusEnum.BUILDING,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await TeamPostgresRepository(pool).create_team(t)
    return t


def _make_invitation(team: Team, owner: Participant, member: Participant) -> Invitation:
    return Invitation(
        id=uuid.uuid4(),
        team_id=team.id,
        owner=owner,
        member=member,
        role=Role(
            id=member.role_id,  # type: ignore
            track_id=team.track_id,
            name="",
            description="",
            count=0,
        ),
        description="join our team",
    )


def _make_join_request(
    team: Team, owner: Participant, member: Participant
) -> JoinRequest:
    return JoinRequest(
        id=uuid.uuid4(),
        team_id=team.id,
        owner=owner,
        member=member,
        role=Role(
            id=member.role_id,  # type: ignore
            track_id=team.track_id,
            name="",
            description="",
            count=0,
        ),
        description="I want in",
    )


@pytest.mark.integration
@pytest.mark.usefixtures("cleanup")
class TestInvitations:
    @pytest.mark.asyncio
    async def test_create_and_get(self, invitation_repository, team, owner, member):
        invitation = _make_invitation(team, owner, member)

        await invitation_repository.create_invitation(invitation)
        fetched = await invitation_repository.get_invitation(invitation.id)

        assert fetched.id == invitation.id
        assert fetched.team_id == team.id
        assert fetched.owner.id == owner.id
        assert fetched.member.id == member.id
        assert fetched.role.id == member.role_id
        assert fetched.description == invitation.description

    @pytest.mark.asyncio
    async def test_get_not_found(self, invitation_repository):
        with pytest.raises(InvitationNotFoundError):
            await invitation_repository.get_invitation(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_duplicate_raises(self, invitation_repository, team, owner, member):
        invitation = _make_invitation(team, owner, member)
        await invitation_repository.create_invitation(invitation)

        duplicate = _make_invitation(team, owner, member)
        with pytest.raises(InvitationAlreadyExistsError):
            await invitation_repository.create_invitation(duplicate)

    @pytest.mark.asyncio
    async def test_create_with_unknown_team_raises(
        self, invitation_repository, owner, member, track
    ):
        fake_team = Team(
            id=uuid.uuid4(),
            track_id=track.id,
            event_id=owner.event_id,
            owner=owner,
            members=[],
            required_roles=[],
            name="",
            description="",
            status=TeamStatusEnum.DRAFT,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        invitation = _make_invitation(fake_team, owner, member)

        with pytest.raises(TeamNotFoundError):
            await invitation_repository.create_invitation(invitation)

    @pytest.mark.asyncio
    async def test_get_invitations_by_team(
        self, invitation_repository, team, owner, member, pool, event_id, track
    ):
        # Two invited members
        other = Participant(
            id=uuid.uuid4(),
            event_id=event_id,
            name="Other",
            surname="S",
            patronymic="P",
            have_team=False,
            role_id=track.required_roles[0].id,
        )
        await EventPostgresRepository(pool).add_participant(event_id, other)

        await invitation_repository.create_invitation(
            _make_invitation(team, owner, member)
        )
        await invitation_repository.create_invitation(
            _make_invitation(team, owner, other)
        )

        result = await invitation_repository.get_invitations_by_team(team.id)
        assert len(result) == 2
        member_ids = {i.member.id for i in result}
        assert member_ids == {member.id, other.id}

    @pytest.mark.asyncio
    async def test_delete_invitation(self, invitation_repository, team, owner, member):
        invitation = _make_invitation(team, owner, member)
        await invitation_repository.create_invitation(invitation)

        await invitation_repository.delete_invitation(invitation.id)

        with pytest.raises(InvitationNotFoundError):
            await invitation_repository.get_invitation(invitation.id)

    @pytest.mark.asyncio
    async def test_delete_not_found(self, invitation_repository):
        with pytest.raises(InvitationNotFoundError):
            await invitation_repository.delete_invitation(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_accept_invitation_adds_member_and_updates_state(
        self, invitation_repository, team, owner, member, pool
    ):
        invitation = _make_invitation(team, owner, member)
        await invitation_repository.create_invitation(invitation)

        accepted = await invitation_repository.accept_invitation(invitation.id)

        assert accepted.member.have_team is True

        # invitation deleted
        with pytest.raises(InvitationNotFoundError):
            await invitation_repository.get_invitation(invitation.id)

        # team_members updated
        async with pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT role_id FROM team_members "
                    "WHERE team_id = %s AND member_id = %s",
                    (str(team.id), str(member.id)),
                )
                row = await cursor.fetchone()
                assert row is not None
                assert uuid.UUID(str(row[0])) == member.role_id

                # event_participants.have_team updated
                await cursor.execute(
                    "SELECT have_team FROM event_participants "
                    "WHERE event_id = %s AND participant_id = %s",
                    (str(team.event_id), str(member.id)),
                )
                ht = await cursor.fetchone()
                assert ht is not None and ht[0] is True

                # team_roles required_count decremented
                await cursor.execute(
                    "SELECT required_count FROM team_roles "
                    "WHERE team_id = %s AND role_id = %s",
                    (str(team.id), str(member.role_id)),
                )
                rc = await cursor.fetchone()
                assert rc is not None
                # Designer originally had count=1; after accept → 0
                assert rc[0] == 0

    @pytest.mark.asyncio
    async def test_accept_invitation_removes_other_pending(
        self, invitation_repository, team, owner, member, pool, event_id, track
    ):
        # Second team with a competing invitation for same member
        second_owner = Participant(
            id=uuid.uuid4(),
            event_id=event_id,
            name="O2",
            surname="S",
            patronymic="P",
            have_team=False,
            role_id=track.required_roles[0].id,
        )
        await EventPostgresRepository(pool).add_participant(event_id, second_owner)
        second_team = Team(
            id=uuid.uuid4(),
            track_id=track.id,
            event_id=event_id,
            owner=second_owner,
            members=[],
            required_roles=[],
            name="Team B",
            description="",
            status=TeamStatusEnum.BUILDING,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await TeamPostgresRepository(pool).create_team(second_team)

        inv_first = _make_invitation(team, owner, member)
        inv_second = _make_invitation(second_team, second_owner, member)
        await invitation_repository.create_invitation(inv_first)
        await invitation_repository.create_invitation(inv_second)

        # Also a join request we should cleanup too
        jr = _make_join_request(second_team, second_owner, member)
        await invitation_repository.create_join_request(jr)

        await invitation_repository.accept_invitation(inv_first.id)

        with pytest.raises(InvitationNotFoundError):
            await invitation_repository.get_invitation(inv_second.id)
        with pytest.raises(JoinRequestNotFoundError):
            await invitation_repository.get_join_request(jr.id)

    @pytest.mark.asyncio
    async def test_accept_invitation_already_in_team_raises(
        self, invitation_repository, team, owner, member, pool
    ):
        invitation = _make_invitation(team, owner, member)
        await invitation_repository.create_invitation(invitation)

        async with pool.connection() as conn:
            await conn.execute(
                "UPDATE event_participants SET have_team = TRUE"
                " WHERE participant_id = %s AND event_id = %s",
                (str(member.id), str(member.event_id)),
            )

        with pytest.raises(ParticipantAlreadyInTeamError):
            await invitation_repository.accept_invitation(invitation.id)


@pytest.mark.integration
@pytest.mark.usefixtures("cleanup")
class TestJoinRequests:
    @pytest.mark.asyncio
    async def test_create_and_get(self, invitation_repository, team, owner, member):
        jr = _make_join_request(team, owner, member)

        await invitation_repository.create_join_request(jr)
        fetched = await invitation_repository.get_join_request(jr.id)

        assert fetched.id == jr.id
        assert fetched.team_id == team.id
        assert fetched.member.id == member.id
        assert fetched.description == jr.description

    @pytest.mark.asyncio
    async def test_get_not_found(self, invitation_repository):
        with pytest.raises(JoinRequestNotFoundError):
            await invitation_repository.get_join_request(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_duplicate_raises(self, invitation_repository, team, owner, member):
        jr = _make_join_request(team, owner, member)
        await invitation_repository.create_join_request(jr)

        with pytest.raises(JoinRequestAlreadyExistsError):
            await invitation_repository.create_join_request(
                _make_join_request(team, owner, member)
            )

    @pytest.mark.asyncio
    async def test_get_by_track_and_member(
        self, invitation_repository, team, owner, member, track
    ):
        jr = _make_join_request(team, owner, member)
        await invitation_repository.create_join_request(jr)

        result = await invitation_repository.get_join_requests_by_track_and_member(
            track.id, member.id
        )
        assert len(result) == 1
        assert result[0].id == jr.id

    @pytest.mark.asyncio
    async def test_get_by_track_and_member_empty(self, invitation_repository, track):
        result = await invitation_repository.get_join_requests_by_track_and_member(
            track.id, uuid.uuid4()
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_delete(self, invitation_repository, team, owner, member):
        jr = _make_join_request(team, owner, member)
        await invitation_repository.create_join_request(jr)

        await invitation_repository.delete_join_request(jr.id)

        with pytest.raises(JoinRequestNotFoundError):
            await invitation_repository.get_join_request(jr.id)

    @pytest.mark.asyncio
    async def test_delete_not_found(self, invitation_repository):
        with pytest.raises(JoinRequestNotFoundError):
            await invitation_repository.delete_join_request(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_accept_join_request(
        self, invitation_repository, team, owner, member, pool
    ):
        jr = _make_join_request(team, owner, member)
        await invitation_repository.create_join_request(jr)

        accepted = await invitation_repository.accept_join_request(jr.id)

        assert accepted.member.have_team is True

        with pytest.raises(JoinRequestNotFoundError):
            await invitation_repository.get_join_request(jr.id)

        async with pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT COUNT(*) FROM team_members "
                    "WHERE team_id = %s AND member_id = %s",
                    (str(team.id), str(member.id)),
                )
                (count,) = await cursor.fetchone()  # type: ignore
                assert count == 1

                await cursor.execute(
                    "SELECT required_count FROM team_roles "
                    "WHERE team_id = %s AND role_id = %s",
                    (str(team.id), str(member.role_id)),
                )
                (rc,) = await cursor.fetchone()  # type: ignore
                assert rc == 0

    @pytest.mark.asyncio
    async def test_accept_join_request_already_in_team_raises(
        self, invitation_repository, team, owner, member, pool
    ):
        jr = _make_join_request(team, owner, member)
        await invitation_repository.create_join_request(jr)

        async with pool.connection() as conn:
            await conn.execute(
                "UPDATE event_participants SET have_team = TRUE"
                " WHERE participant_id = %s AND event_id = %s",
                (str(member.id), str(member.event_id)),
            )

        with pytest.raises(ParticipantAlreadyInTeamError):
            await invitation_repository.accept_join_request(jr.id)
