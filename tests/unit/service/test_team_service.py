# import uuid
# from datetime import datetime
# from unittest.mock import AsyncMock

# import pytest

# import src.adapters.repository.errors as adapter_errors
# import src.service.errors as service_errors
# from src.models.team import Team, TeamStatusEnum
# from src.service.team.service import TeamService


# def make_team(**kwargs) -> Team:
#     defaults = dict(
#         id=uuid.uuid4(),
#         name="Test Team",
#         description="A test team",
#         track_id=uuid.uuid4(),
#         event_id=uuid.uuid4(),
#         owner_id=uuid.uuid4(),
#         member_ids=[],
#         required_roles=[],
#         status=TeamStatusEnum.DRAFT,
#         created_at=datetime.now(),
#         updated_at=datetime.now(),
#     )
#     defaults.update(kwargs)
#     return Team(**defaults)  # type: ignore


# @pytest.fixture
# def team_repo():
#     return AsyncMock()


# @pytest.fixture
# def kafka_producer():
#     return AsyncMock()


# @pytest.fixture
# def service(team_repo, kafka_producer):
#     return TeamService(
#         team_repository=team_repo,
#         kafka_producer=kafka_producer,
#     )


# @pytest.mark.unit
# class TestGetTeams:
#     @pytest.mark.asyncio
#     async def test_returns_team(self, service, team_repo):
#         team = make_team()
#         team_repo.get_team.return_value = team

#         result = await service.get_teams(team.id)

#         assert result == team
#         team_repo.get_team.assert_called_once_with(team.id)

#     @pytest.mark.asyncio
#     async def test_raises_team_not_found(self, service, team_repo):
#         team_repo.get_team.side_effect = adapter_errors.TeamNotFoundError

#         with pytest.raises(service_errors.TeamNotFoundError):
#             await service.get_teams(uuid.uuid4())


# @pytest.mark.unit
# class TestCreateTeam:
#     @pytest.mark.asyncio
#     async def test_returns_id(self, service, team_repo, kafka_producer):
#         team = make_team()

#         result = await service.create_team(team)

#         assert isinstance(result, uuid.UUID)
#         team_repo.create_team.assert_called_once_with(team)
#         kafka_producer.send_team_created.assert_called_once_with(team)


# @pytest.mark.unit
# class TestUpdateTeam:
#     @pytest.mark.asyncio
#     async def test_calls_repo_and_kafka(self, service, team_repo, kafka_producer):
#         team = make_team()

#         await service.update_team(team)

#         team_repo.update_team.assert_called_once_with(team)
#         kafka_producer.send_team_updated.assert_called_once_with(team)

#     @pytest.mark.asyncio
#     async def test_raises_when_not_found(self, service, team_repo, kafka_producer):
#         team = make_team()
#         team_repo.update_team.side_effect = adapter_errors.TeamNotFoundError

#         with pytest.raises(service_errors.TeamNotFoundError):
#             await service.update_team(team)

#         kafka_producer.send_team_updated.assert_not_called()


# @pytest.mark.unit
# class TestDeleteTeam:
#     @pytest.mark.asyncio
#     async def test_calls_repo_and_kafka(self, service, team_repo, kafka_producer):
#         team_id = uuid.uuid4()

#         await service.delete_team(team_id)

#         team_repo.delete_team.assert_called_once_with(team_id)
#         kafka_producer.send_team_deleted.assert_called_once_with(team_id)

#     @pytest.mark.asyncio
#     async def test_raises_when_not_found(self, service, team_repo, kafka_producer):
#         team_repo.delete_team.side_effect = adapter_errors.TeamNotFoundError

#         with pytest.raises(service_errors.TeamNotFoundError):
#             await service.delete_team(uuid.uuid4())

#         kafka_producer.send_team_deleted.assert_not_called()


# @pytest.mark.unit
# class TestLeaveTeam:
#     @pytest.mark.asyncio
#     async def test_calls_remove_member_and_kafka(
#         self, service, team_repo, kafka_producer
#     ):
#         team_id = uuid.uuid4()
#         user_id = uuid.uuid4()
#         owner_id = uuid.uuid4()

#         team = make_team(id=team_id, owner_id=owner_id, member_ids=[owner_id, user_id])
#         team_repo.get_team.return_value = team

#         await service.leave_team(team_id, user_id)

#         team_repo.remove_member.assert_called_once_with(team_id, user_id)
#         kafka_producer.send_member_left.assert_called_once_with(
#             team_id, user_id, team.event_id
#         )

#     @pytest.mark.asyncio
#     async def test_raises_when_user_not_member(self, service, team_repo):
#         team_id = uuid.uuid4()
#         user_id = uuid.uuid4()

#         team = make_team(id=team_id, member_ids=[])
#         team_repo.get_team.return_value = team

#         with pytest.raises(service_errors.UserNotFoundError):
#             await service.leave_team(team_id, user_id)

#     @pytest.mark.asyncio
#     async def test_raises_when_owner_tries_to_leave(self, service, team_repo):
#         team_id = uuid.uuid4()
#         owner_id = uuid.uuid4()

#         team = make_team(id=team_id, owner_id=owner_id, member_ids=[owner_id])
#         team_repo.get_team.return_value = team

#         with pytest.raises(service_errors.TeamOperationError):
#             await service.leave_team(team_id, owner_id)


# @pytest.mark.unit
# class TestKickMember:
#     @pytest.mark.asyncio
#     async def test_calls_remove_member_and_kafka(
#         self, service, team_repo, kafka_producer
#     ):
#         team_id = uuid.uuid4()
#         user_id = uuid.uuid4()
#         owner_id = uuid.uuid4()

#         team = make_team(id=team_id, owner_id=owner_id, member_ids=[owner_id, user_id])
#         team_repo.get_team.return_value = team

#         await service.kick_member(team_id, user_id)

#         team_repo.remove_member.assert_called_once_with(team_id, user_id)
#         kafka_producer.send_member_kicked.assert_called_once_with(
#             team_id, user_id, owner_id, team.event_id
#         )

#     @pytest.mark.asyncio
#     async def test_raises_when_user_not_member(self, service, team_repo):
#         team_id = uuid.uuid4()
#         user_id = uuid.uuid4()

#         team = make_team(id=team_id, member_ids=[])
#         team_repo.get_team.return_value = team

#         with pytest.raises(service_errors.UserNotFoundError):
#             await service.kick_member(team_id, user_id)

#     @pytest.mark.asyncio
#     async def test_raises_when_cannot_kick_owner(self, service, team_repo):
#         team_id = uuid.uuid4()
#         owner_id = uuid.uuid4()

#         team = make_team(id=team_id, owner_id=owner_id, member_ids=[owner_id])
#         team_repo.get_team.return_value = team

#         with pytest.raises(service_errors.TeamOperationError):
#             await service.kick_member(team_id, owner_id)


# @pytest.mark.unit
# class TestTeamSubmit:
#     @pytest.mark.asyncio
#     async def test_calls_change_status_and_kafka(
#         self, service, team_repo, kafka_producer
#     ):
#         team_id = uuid.uuid4()
#         submission_url = "https://example.com/submission"

#         team = make_team(id=team_id, status=TeamStatusEnum.FULL)
#         team_repo.get_team.return_value = team

#         await service.team_submit(team_id, submission_url)

#         team_repo.change_team_status.assert_called_once_with(
#             team_id, TeamStatusEnum.SUBMITTED.value
#         )
#         kafka_producer.send_team_submitted.assert_called_once_with(
#             team_id, submission_url, team.event_id, team.track_id
#         )

#     @pytest.mark.asyncio
#     async def test_raises_when_team_not_full(self, service, team_repo):
#         team_id = uuid.uuid4()
#         submission_url = "https://example.com/submission"

#         team = make_team(id=team_id, status=TeamStatusEnum.DRAFT)
#         team_repo.get_team.return_value = team

#         with pytest.raises(service_errors.TeamOperationError):
#             await service.team_submit(team_id, submission_url)

#     @pytest.mark.asyncio
#     async def test_raises_when_team_not_found(self, service, team_repo):
#         team_id = uuid.uuid4()
#         submission_url = "https://example.com/submission"

#         team_repo.get_team.side_effect = adapter_errors.TeamNotFoundError

#         with pytest.raises(service_errors.TeamNotFoundError):
#             await service.team_submit(team_id, submission_url)


# @pytest.mark.unit
# class TestChangeTeamStatus:
#     @pytest.mark.asyncio
#     async def test_calls_change_team_status(self, service, team_repo):
#         team_id = uuid.uuid4()
#         new_status = TeamStatusEnum.BUILDING

#         await service.change_team_status(team_id, new_status)

#         team_repo.change_team_status.assert_called_once_with(team_id, new_status.value)

#     @pytest.mark.asyncio
#     async def test_raises_when_team_not_found(self, service, team_repo):
#         team_repo.change_team_status.side_effect = adapter_errors.TeamNotFoundError

#         with pytest.raises(service_errors.TeamNotFoundError):
#             await service.change_team_status(uuid.uuid4(), TeamStatusEnum.BUILDING)
