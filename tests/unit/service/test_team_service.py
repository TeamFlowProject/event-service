import uuid
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

import src.adapters.repository.errors as adapter_errors
import src.service.errors as service_errors
from src.models.team import Team, TeamStatusEnum, Role
from src.service.team.service import TeamService


def make_team(**kwargs) -> Team:
    defaults = dict(
        id=uuid.uuid4(),
        name="Test Team",
        description="A test team",
        track_id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        member_ids=[uuid.uuid4()],
        required_roles=[],
        status=TeamStatusEnum.DRAFT,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    defaults.update(kwargs)
    return Team(**defaults)  # type: ignore


def make_role(**kwargs) -> Role:
    defaults = dict(
        id=uuid.uuid4(),
        name="Developer",
        description="Python developer",
        count=2,
    )
    defaults.update(kwargs)
    return Role(**defaults)  # type: ignore


def make_create_request(**kwargs) -> CreateTeamRequestDTO:
    defaults = dict(
        name="New Team",
        description="New team description",
        track_id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        required_roles=[],
    )
    defaults.update(kwargs)
    return CreateTeamRequestDTO(**defaults)  # type: ignore


def make_update_request(**kwargs) -> UpdateTeamRequestDTO:
    defaults = dict(
        name="Updated Team",
        description="Updated description",
        required_roles=None,
    )
    defaults.update(kwargs)
    return UpdateTeamRequestDTO(**defaults)  # type: ignore


@pytest.fixture
def team_repo():
    return AsyncMock()


@pytest.fixture
def user_repo():
    return AsyncMock()


@pytest.fixture
def event_client():
    return AsyncMock()


@pytest.fixture
def track_client():
    return AsyncMock()


@pytest.fixture
def kafka_producer():
    return AsyncMock()


@pytest.fixture
def service(team_repo, user_repo, event_client, track_client, kafka_producer):
    return TeamService(
        team_repository=team_repo,
        event_client=event_client,
        track_client=track_client,
        kafka_producer=kafka_producer,
    )


@pytest.mark.unit
class TestGetTeams:
    @pytest.mark.asyncio
    async def test_returns_team(self, service, team_repo):
        team = make_team()
        team_repo.get_team.return_value = team

        result = await service.get_teams(team.id)

        assert result == team
        team_repo.get_team.assert_called_once_with(team.id)

    @pytest.mark.asyncio
    async def test_raises_team_not_found(self, service, team_repo):
        team_repo.get_team.side_effect = adapter_errors.TeamNotFoundError

        with pytest.raises(service_errors.TeamNotFoundError):
            await service.get_teams(uuid.uuid4())



@pytest.mark.unit
class TestCreateTeam:
    @pytest.mark.asyncio
    async def test_returns_id(self, service, event_client, track_client, team_repo):
        event_client.event_exists.return_value = True
        track_client.track_exists.return_value = True
        team_repo.get_teams_by_user.return_value = []
        
        team = Team(
            id=uuid.uuid4(),
            name="New Team",
            description="New team description",
            track_id=uuid.uuid4(),
            event_id=uuid.uuid4(),
            owner_id=uuid.uuid4(),
            member_ids=[],
            required_roles=[],
            status=TeamStatusEnum.DRAFT,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        result = await service.create_team(team)

        assert isinstance(result, uuid.UUID)

    @pytest.mark.asyncio
    async def test_calls_repo_and_kafka(self, service, event_client, track_client, user_repo, team_repo, kafka_producer):
        event_client.event_exists.return_value = True
        track_client.track_exists.return_value = True
        user_repo.user_exists.return_value = True
        team_repo.get_teams_by_user.return_value = []
        
        request = make_create_request()

        await service.create_team(request)

        team_repo.create_team.assert_called_once()
        kafka_producer.send_team_created.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_event_not_found(self, service, event_client):
        event_client.event_exists.return_value = False
        
        request = make_create_request()

        with pytest.raises(service_errors.EventNotFoundError):
            await service.create_team(request)

    @pytest.mark.asyncio
    async def test_raises_track_not_found(self, service, event_client, track_client):
        event_client.event_exists.return_value = True
        track_client.track_exists.return_value = False
        
        request = make_create_request()

        with pytest.raises(service_errors.TrackNotFoundError):
            await service.create_team(request)

    @pytest.mark.asyncio
    async def test_raises_user_not_found(self, service, event_client, track_client, user_repo):
        event_client.event_exists.return_value = True
        track_client.track_exists.return_value = True
        user_repo.user_exists.return_value = False
        
        request = make_create_request()

        with pytest.raises(service_errors.UserNotFoundError):
            await service.create_team(request)

    @pytest.mark.asyncio
    async def test_raises_team_already_exists(self, service, event_client, track_client, user_repo, team_repo):
        event_client.event_exists.return_value = True
        track_client.track_exists.return_value = True
        user_repo.user_exists.return_value = True
        
        existing_team = make_team(track_id=uuid.uuid4())
        team_repo.get_teams_by_user.return_value = [existing_team]
        
        request = make_create_request(track_id=existing_team.track_id)

        with pytest.raises(service_errors.TeamAlreadyExistsError):
            await service.create_team(request)


@pytest.mark.unit
class TestUpdateTeam:
    @pytest.mark.asyncio
    async def test_calls_repo_and_kafka(self, service, team_repo, kafka_producer):
        team = make_team()
        team_repo.get_team.return_value = team
        
        request = make_update_request()

        await service.update_team(team.id, request)

        team_repo.update_team.assert_called_once()
        kafka_producer.send_team_updated.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_service_error_when_not_found(self, service, team_repo, kafka_producer):
        team_repo.get_team.side_effect = adapter_errors.TeamNotFoundError
        
        request = make_update_request()

        with pytest.raises(service_errors.TeamNotFoundError):
            await service.update_team(uuid.uuid4(), request)

        kafka_producer.send_team_updated.assert_not_called()


@pytest.mark.unit
class TestDeleteTeam:
    @pytest.mark.asyncio
    async def test_calls_repo_and_kafka(self, service, team_repo, kafka_producer):
        team_id = uuid.uuid4()

        await service.delete_team(team_id)

        team_repo.delete_team.assert_called_once_with(team_id)
        kafka_producer.send_team_deleted.assert_called_once_with(team_id)

    @pytest.mark.asyncio
    async def test_raises_service_error_when_not_found(self, service, team_repo, kafka_producer):
        team_repo.delete_team.side_effect = adapter_errors.TeamNotFoundError

        with pytest.raises(service_errors.TeamNotFoundError):
            await service.delete_team(uuid.uuid4())

        kafka_producer.send_team_deleted.assert_not_called()


@pytest.mark.unit
class TestLeaveTeam:
    @pytest.mark.asyncio
    async def test_calls_repo_and_kafka(self, service, team_repo, kafka_producer):
        team_id = uuid.uuid4()
        user_id = uuid.uuid4()
        owner_id = uuid.uuid4()
        
        team = make_team(id=team_id, owner_id=owner_id, member_ids=[owner_id, user_id])
        team_repo.get_team.return_value = team

        await service.leave_team(team_id, user_id)

        team_repo.kick_member.assert_called_once_with(team_id, user_id)
        kafka_producer.send_member_left.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_when_user_not_member(self, service, team_repo):
        team_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        team = make_team(id=team_id, member_ids=[])
        team_repo.get_team.return_value = team

        with pytest.raises(service_errors.UserNotFoundError):
            await service.leave_team(team_id, user_id)

    @pytest.mark.asyncio
    async def test_raises_when_owner_tries_to_leave(self, service, team_repo):
        team_id = uuid.uuid4()
        owner_id = uuid.uuid4()
        
        team = make_team(id=team_id, owner_id=owner_id, member_ids=[owner_id])
        team_repo.get_team.return_value = team

        with pytest.raises(service_errors.TeamOperationError):
            await service.leave_team(team_id, owner_id)


@pytest.mark.unit
class TestKickMember:
    @pytest.mark.asyncio
    async def test_calls_repo_and_kafka(self, service, team_repo, kafka_producer):
        team_id = uuid.uuid4()
        user_id = uuid.uuid4()
        owner_id = uuid.uuid4()
        
        team = make_team(id=team_id, owner_id=owner_id, member_ids=[owner_id, user_id])
        team_repo.get_team.return_value = team

        await service.kick_member(team_id, user_id)

        team_repo.kick_member.assert_called_once_with(team_id, user_id)
        kafka_producer.send_member_kicked.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_when_cannot_kick_owner(self, service, team_repo):
        team_id = uuid.uuid4()
        owner_id = uuid.uuid4()
        
        team = make_team(id=team_id, owner_id=owner_id, member_ids=[owner_id])
        team_repo.get_team.return_value = team

        with pytest.raises(service_errors.TeamOperationError):
            await service.kick_member(team_id, owner_id)


@pytest.mark.unit
class TestTeamSubmit:
    @pytest.mark.asyncio
    async def test_calls_repo_and_kafka(self, service, team_repo, kafka_producer):
        team_id = uuid.uuid4()
        submission_url = "https://example.com/submission"
        
        team = make_team(id=team_id, status=TeamStatusEnum.FULL)
        team_repo.get_team.return_value = team

        await service.team_submit(team_id, submission_url)

        team_repo.team_submit.assert_called_once_with(team_id, submission_url)
        kafka_producer.send_team_submitted.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_when_team_not_full(self, service, team_repo):
        team_id = uuid.uuid4()
        submission_url = "https://example.com/submission"
        
        team = make_team(id=team_id, status=TeamStatusEnum.DRAFT)
        team_repo.get_team.return_value = team

        with pytest.raises(service_errors.TeamOperationError):
            await service.team_submit(team_id, submission_url)


@pytest.mark.unit
class TestUpdateMember:
    @pytest.mark.asyncio
    async def test_calls_repo_and_kafka(self, service, team_repo, kafka_producer):
        team_id = uuid.uuid4()
        user_id = uuid.uuid4()
        role = "co-captain"
        
        team = make_team(id=team_id, owner_id=uuid.uuid4(), member_ids=[user_id])
        team_repo.get_team.return_value = team

        await service.update_member(team_id, user_id, role)

        team_repo.update_member.assert_called_once_with(team_id, user_id, role)
        kafka_producer.send_member_updated.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_when_updating_owner(self, service, team_repo):
        team_id = uuid.uuid4()
        owner_id = uuid.uuid4()
        role = "new_role"
        
        team = make_team(id=team_id, owner_id=owner_id, member_ids=[owner_id])
        team_repo.get_team.return_value = team

        with pytest.raises(service_errors.TeamOperationError):
            await service.update_member(team_id, owner_id, role)


@pytest.mark.unit
class TestChangeTeamStatus:
    @pytest.mark.asyncio
    async def test_calls_repo_and_kafka(self, service, team_repo, kafka_producer):
        team_id = uuid.uuid4()
        new_status = TeamStatusEnum.BUILDING
        
        team = make_team(id=team_id, status=TeamStatusEnum.DRAFT)
        team_repo.get_team.return_value = team

        await service.change_team_status(team_id, new_status)

        team_repo.change_team_status.assert_called_once_with(team_id, new_status.value)
        kafka_producer.send_team_status_changed.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_when_team_not_found(self, service, team_repo):
        team_repo.get_team.side_effect = adapter_errors.TeamNotFoundError

        with pytest.raises(service_errors.TeamNotFoundError):
            await service.change_team_status(uuid.uuid4(), TeamStatusEnum.BUILDING)


@pytest.mark.unit
class TestAddMember:
    @pytest.mark.asyncio
    async def test_calls_repo_and_kafka(self, service, team_repo, user_repo, kafka_producer):
        team_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        team = make_team(id=team_id, track_id=uuid.uuid4(), member_ids=[])
        team_repo.get_team.return_value = team
        user_repo.user_exists.return_value = True
        team_repo.get_teams_by_user.return_value = []

        await service.add_member(team_id, user_id)

        team_repo.add_member.assert_called_once_with(team_id, user_id)
        kafka_producer.send_member_added.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_when_user_not_exists(self, service, team_repo, user_repo):
        team_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        team = make_team(id=team_id)
        team_repo.get_team.return_value = team
        user_repo.user_exists.return_value = False

        with pytest.raises(service_errors.UserNotFoundError):
            await service.add_member(team_id, user_id)

    @pytest.mark.asyncio
    async def test_raises_when_user_already_member(self, service, team_repo, user_repo):
        team_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        team = make_team(id=team_id, member_ids=[user_id])
        team_repo.get_team.return_value = team
        user_repo.user_exists.return_value = True

        with pytest.raises(service_errors.UserNotFoundError):
            await service.add_member(team_id, user_id)

    @pytest.mark.asyncio
    async def test_raises_when_user_has_team_in_same_track(self, service, team_repo, user_repo):
        team_id = uuid.uuid4()
        user_id = uuid.uuid4()
        track_id = uuid.uuid4()
        
        team = make_team(id=team_id, track_id=track_id, member_ids=[])
        team_repo.get_team.return_value = team
        user_repo.user_exists.return_value = True
        
        existing_team = make_team(track_id=track_id)
        team_repo.get_teams_by_user.return_value = [existing_team]

        with pytest.raises(service_errors.TeamAlreadyExistsError):
            await service.add_member(team_id, user_id)