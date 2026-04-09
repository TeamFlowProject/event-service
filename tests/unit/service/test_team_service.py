import uuid
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

import src.adapters.repository.errors as adapter_errors
import src.service.errors as service_errors
from src.models.team import Team, TeamStatusEnum
from src.models.event import Participant
from src.service.team.service import TeamService


def make_participant(**kwargs) -> Participant:
    defaults = dict(
        id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        name="John",
        surname="Doe",
        patronymic="Smith",
        have_team=False,
    )
    defaults.update(kwargs)
    return Participant(**defaults)  # type: ignore


def make_team(**kwargs) -> Team:
    owner = make_participant()
    defaults = dict(
        id=uuid.uuid4(),
        track_id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        owner=owner,
        members=[owner],
        required_roles=[],
        name="Test Team",
        description="A test team",
        status=TeamStatusEnum.DRAFT,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    defaults.update(kwargs)
    return Team(**defaults)  # type: ignore


@pytest.fixture
def repo():
    return AsyncMock()


@pytest.fixture
def kafka():
    return AsyncMock()


@pytest.fixture
def service(repo, kafka):
    return TeamService(team_repository=repo, kafka_producer=kafka)


@pytest.mark.unit
class TestGetTeam:
    @pytest.mark.asyncio
    async def test_returns_team(self, service, repo):
        team = make_team()
        repo.get_team.return_value = team

        result = await service.get_teams(team.id)

        assert result == team
        repo.get_team.assert_called_once_with(team.id)

    @pytest.mark.asyncio
    async def test_raises_team_not_found(self, service, repo):
        repo.get_team.side_effect = adapter_errors.TeamNotFoundError

        with pytest.raises(service_errors.TeamNotFoundError):
            await service.get_teams(uuid.uuid4())


@pytest.mark.unit
class TestCreateTeam:
    @pytest.mark.asyncio
    async def test_returns_id(self, service, repo, kafka):
        team = make_team()
        team.owner.have_team = False
        repo.create_team.return_value = None

        result = await service.create_team(team)

        assert isinstance(result, uuid.UUID)
        repo.create_team.assert_called_once_with(team)
        kafka.send_team_created.assert_called_once_with(team)

    @pytest.mark.asyncio
    async def test_calls_repo_and_kafka(self, service, repo, kafka):
        team = make_team()
        team.owner.have_team = False
        repo.create_team.return_value = None

        await service.create_team(team)

        repo.create_team.assert_called_once_with(team)
        kafka.send_team_created.assert_called_once_with(team)

    @pytest.mark.asyncio
    async def test_raises_error_when_participant_already_in_team(
        self, service, repo, kafka
    ):
        team = make_team()
        team.owner.have_team = True  # участник уже в команде

        with pytest.raises(service_errors.ParticipantAlreadyInTeam):
            await service.create_team(team)

        repo.create_team.assert_not_called()
        kafka.send_team_created.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_event_not_found_error(self, service, repo, kafka):
        team = make_team()
        team.owner.have_team = False
        repo.create_team.side_effect = adapter_errors.EventNotFoundError

        with pytest.raises(service_errors.EventNotFoundError):
            await service.create_team(team)

        kafka.send_team_created.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_participant_not_found_error(self, service, repo, kafka):
        team = make_team()
        team.owner.have_team = False
        repo.create_team.side_effect = adapter_errors.ParticipantNotFoundError

        with pytest.raises(service_errors.ParticipantNotFoundError):
            await service.create_team(team)

        kafka.send_team_created.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_track_not_found_error(self, service, repo, kafka):
        team = make_team()
        team.owner.have_team = False
        repo.create_team.side_effect = adapter_errors.TrackNotFoundError

        with pytest.raises(service_errors.TrackNotFoundError):
            await service.create_team(team)

        kafka.send_team_created.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_team_already_exists_error(self, service, repo, kafka):
        team = make_team()
        team.owner.have_team = False
        repo.create_team.side_effect = adapter_errors.TeamAlreadyExistsError

        with pytest.raises(service_errors.TeamAlreadyExistsError):
            await service.create_team(team)

        kafka.send_team_created.assert_not_called()


@pytest.mark.unit
class TestUpdateTeam:
    @pytest.mark.asyncio
    async def test_calls_repo_and_kafka(self, service, repo, kafka):
        team = make_team()
        repo.update_team.return_value = None

        await service.update_team(team)

        repo.update_team.assert_called_once_with(team)
        kafka.send_team_updated.assert_called_once_with(team)

    @pytest.mark.asyncio
    async def test_raises_service_error_when_team_not_found(self, service, repo, kafka):
        repo.update_team.side_effect = adapter_errors.TeamNotFoundError

        with pytest.raises(service_errors.TeamNotFoundError):
            await service.update_team(make_team())

        kafka.send_team_updated.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_track_not_found_error(self, service, repo, kafka):
        repo.update_team.side_effect = adapter_errors.TrackNotFoundError

        with pytest.raises(service_errors.TrackNotFoundError):
            await service.update_team(make_team())

        kafka.send_team_updated.assert_not_called()


@pytest.mark.unit
class TestDeleteTeam:
    @pytest.mark.asyncio
    async def test_calls_repo_and_kafka(self, service, repo, kafka):
        team_id = uuid.uuid4()
        team = make_team(id=team_id)
        repo.get_team.return_value = team
        repo.delete_team.return_value = None

        await service.delete_team(team_id)

        repo.get_team.assert_called_once_with(team_id)
        repo.delete_team.assert_called_once_with(team_id)
        kafka.send_team_deleted.assert_called_once_with(team)

    @pytest.mark.asyncio
    async def test_raises_service_error_when_team_not_found(self, service, repo, kafka):
        repo.get_team.side_effect = adapter_errors.TeamNotFoundError

        with pytest.raises(service_errors.TeamNotFoundError):
            await service.delete_team(uuid.uuid4())

        repo.delete_team.assert_not_called()
        kafka.send_team_deleted.assert_not_called()


@pytest.mark.unit
class TestLeaveTeam:
    @pytest.mark.asyncio
    async def test_calls_repo_and_kafka(self, service, repo, kafka):
        team_id = uuid.uuid4()
        member_id = uuid.uuid4()
        owner = make_participant(id=uuid.uuid4())
        member = make_participant(id=member_id)
        team = make_team(id=team_id, owner=owner, members=[owner, member])

        repo.get_team.return_value = team
        repo.get_member_by_id.return_value = member
        repo.remove_member.return_value = None

        await service.leave_team(team_id, member_id)

        repo.get_team.assert_called_once_with(team_id)
        repo.get_member_by_id.assert_called_once_with(member_id)
        repo.remove_member.assert_called_once_with(team_id, member_id)
        kafka.send_member_left.assert_called_once_with(team, member)

    @pytest.mark.asyncio
    async def test_raises_error_when_member_not_in_team(self, service, repo, kafka):
        team_id = uuid.uuid4()
        member_id = uuid.uuid4()
        owner = make_participant()
        member = make_participant(id=member_id)
        team = make_team(id=team_id, owner=owner, members=[owner])

        repo.get_team.return_value = team
        repo.get_member_by_id.return_value = member

        with pytest.raises(service_errors.ParticipantNotFoundError):
            await service.leave_team(team_id, member_id)

        repo.remove_member.assert_not_called()
        kafka.send_member_left.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_error_when_owner_tries_to_leave(self, service, repo, kafka):
        team_id = uuid.uuid4()
        owner_id = uuid.uuid4()
        owner = make_participant(id=owner_id)
        team = make_team(id=team_id, owner=owner, members=[owner])

        repo.get_team.return_value = team
        repo.get_member_by_id.return_value = owner

        with pytest.raises(service_errors.TeamOperationError):
            await service.leave_team(team_id, owner_id)

        repo.remove_member.assert_not_called()
        kafka.send_member_left.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_service_error_when_team_not_found(self, service, repo, kafka):
        repo.get_team.side_effect = adapter_errors.TeamNotFoundError

        with pytest.raises(service_errors.TeamNotFoundError):
            await service.leave_team(uuid.uuid4(), uuid.uuid4())


@pytest.mark.unit
class TestKickMember:
    @pytest.mark.asyncio
    async def test_calls_repo_and_kafka(self, service, repo, kafka):
        team_id = uuid.uuid4()
        member_id = uuid.uuid4()
        owner = make_participant(id=uuid.uuid4())
        member = make_participant(id=member_id)
        team = make_team(id=team_id, owner=owner, members=[owner, member])

        repo.get_team.return_value = team
        repo.get_member_by_id.return_value = member
        repo.remove_member.return_value = None

        await service.kick_member(team_id, member_id)

        repo.get_team.assert_called_once_with(team_id)
        repo.get_member_by_id.assert_called_once_with(member_id)
        repo.remove_member.assert_called_once_with(team_id, member_id)
        kafka.send_member_kicked.assert_called_once_with(team, member)

    @pytest.mark.asyncio
    async def test_raises_error_when_member_not_in_team(self, service, repo, kafka):
        team_id = uuid.uuid4()
        member_id = uuid.uuid4()
        owner = make_participant()
        member = make_participant(id=member_id)
        team = make_team(id=team_id, owner=owner, members=[owner])

        repo.get_team.return_value = team
        repo.get_member_by_id.return_value = member

        with pytest.raises(service_errors.ParticipantNotFoundError):
            await service.kick_member(team_id, member_id)

        repo.remove_member.assert_not_called()
        kafka.send_member_kicked.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_error_when_trying_to_kick_owner(self, service, repo, kafka):
        team_id = uuid.uuid4()
        owner_id = uuid.uuid4()
        owner = make_participant(id=owner_id)
        team = make_team(id=team_id, owner=owner, members=[owner])

        repo.get_team.return_value = team
        repo.get_member_by_id.return_value = owner

        with pytest.raises(service_errors.TeamOperationError):
            await service.kick_member(team_id, owner_id)

        repo.remove_member.assert_not_called()
        kafka.send_member_kicked.assert_not_called()


@pytest.mark.unit
class TestTeamSubmit:
    @pytest.mark.asyncio
    async def test_calls_repo_and_kafka(self, service, repo, kafka):
        team_id = uuid.uuid4()
        team = make_team(id=team_id, status=TeamStatusEnum.FULL)
        repo.get_team.return_value = team
        repo.change_team_status.return_value = None

        await service.team_submit(team_id)

        repo.get_team.assert_called_once_with(team_id)
        repo.change_team_status.assert_called_once_with(
            team_id, TeamStatusEnum.SUBMITTED
        )
        kafka.send_team_submitted.assert_called_once_with(team)

    @pytest.mark.asyncio
    async def test_raises_error_when_status_is_draft(self, service, repo, kafka):
        team_id = uuid.uuid4()
        team = make_team(id=team_id, status=TeamStatusEnum.DRAFT)
        repo.get_team.return_value = team

        with pytest.raises(service_errors.TeamOperationError):
            await service.team_submit(team_id)

        repo.change_team_status.assert_not_called()
        kafka.send_team_submitted.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_error_when_status_is_submitted(self, service, repo, kafka):
        team_id = uuid.uuid4()
        team = make_team(id=team_id, status=TeamStatusEnum.SUBMITTED)
        repo.get_team.return_value = team

        with pytest.raises(service_errors.TeamOperationError):
            await service.team_submit(team_id)

        repo.change_team_status.assert_not_called()
        kafka.send_team_submitted.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_error_when_status_is_confirmed(self, service, repo, kafka):
        team_id = uuid.uuid4()
        team = make_team(id=team_id, status=TeamStatusEnum.CONFIRMED)
        repo.get_team.return_value = team

        with pytest.raises(service_errors.TeamOperationError):
            await service.team_submit(team_id)

        repo.change_team_status.assert_not_called()
        kafka.send_team_submitted.assert_not_called()

    @pytest.mark.asyncio
    async def test_allows_submit_when_status_is_building(self, service, repo, kafka):
        team_id = uuid.uuid4()
        team = make_team(id=team_id, status=TeamStatusEnum.BUILDING)
        repo.get_team.return_value = team
        repo.change_team_status.return_value = None

        await service.team_submit(team_id)

        repo.change_team_status.assert_called_once_with(
            team_id, TeamStatusEnum.SUBMITTED
        )
        kafka.send_team_submitted.assert_called_once_with(team)

    @pytest.mark.asyncio
    async def test_allows_submit_when_status_is_validated(self, service, repo, kafka):
        team_id = uuid.uuid4()
        team = make_team(id=team_id, status=TeamStatusEnum.VALIDATED)
        repo.get_team.return_value = team
        repo.change_team_status.return_value = None

        await service.team_submit(team_id)

        repo.change_team_status.assert_called_once_with(
            team_id, TeamStatusEnum.SUBMITTED
        )
        kafka.send_team_submitted.assert_called_once_with(team)

    @pytest.mark.asyncio
    async def test_allows_submit_when_status_is_rejected(self, service, repo, kafka):
        team_id = uuid.uuid4()
        team = make_team(id=team_id, status=TeamStatusEnum.REJECTED)
        repo.get_team.return_value = team
        repo.change_team_status.return_value = None

        await service.team_submit(team_id)

        repo.change_team_status.assert_called_once_with(
            team_id, TeamStatusEnum.SUBMITTED
        )
        kafka.send_team_submitted.assert_called_once_with(team)

    @pytest.mark.asyncio
    async def test_allows_submit_when_status_is_invalid(self, service, repo, kafka):
        team_id = uuid.uuid4()
        team = make_team(id=team_id, status=TeamStatusEnum.INVALID)
        repo.get_team.return_value = team
        repo.change_team_status.return_value = None

        await service.team_submit(team_id)

        repo.change_team_status.assert_called_once_with(
            team_id, TeamStatusEnum.SUBMITTED
        )
        kafka.send_team_submitted.assert_called_once_with(team)


@pytest.mark.unit
class TestChangeTeamStatus:
    @pytest.mark.asyncio
    async def test_calls_repo(self, service, repo):
        team_id = uuid.uuid4()
        status = TeamStatusEnum.VALIDATED
        repo.change_team_status.return_value = None

        await service.change_team_status(team_id, status)

        repo.change_team_status.assert_called_once_with(team_id, status)

    @pytest.mark.asyncio
    async def test_raises_service_error_when_team_not_found(self, service, repo):
        repo.change_team_status.side_effect = adapter_errors.TeamNotFoundError

        with pytest.raises(service_errors.TeamNotFoundError):
            await service.change_team_status(uuid.uuid4(), TeamStatusEnum.VALIDATED)
