from src.service.team.protocols import TeamRepository, KafkaProducer
from src.models.team import Team, TeamStatusEnum
import uuid
import src.adapters.repository.errors as adapter_errors
import src.service.errors as service_errors


class TeamService:
    def __init__(
        self,
        team_repository: TeamRepository,
        kafka_producer: KafkaProducer,
    ) -> None:
        self._team_repository = team_repository
        self._kafka_producer = kafka_producer

    async def get_team(self, team_id: uuid.UUID) -> Team:
        try:
            return await self._team_repository.get_team(team_id)
        except adapter_errors.TeamNotFoundError as e:
            raise service_errors.TeamNotFoundError("Failed to get team") from e


    async def get_teams_by_event(self, event_id: uuid.UUID) -> list[Team]:
        try:
            return await self._team_repository.get_teams_by_event(event_id)
        except adapter_errors.EventNotFoundError as e:
            raise service_errors.EventNotFoundError("Failed to get teams by event") from e

    async def get_teams_by_user(self, user_id: uuid.UUID) -> list[Team]:
        try:
            return await self._team_repository.get_teams_by_user(user_id)
        except adapter_errors.UserNotFoundError as e:
            raise service_errors.UserNotFoundError("Failed to get teams by user") from e

    async def create_team(self, team: Team) -> uuid.UUID:
        await self._team_repository.create_team(team)
        await self._kafka_producer.send_team_created(team)
        return team.id

    async def update_team(self, team: Team) -> None:
        try:
            await self._team_repository.update_team(team)
            await self._kafka_producer.send_team_updated(team)
        except adapter_errors.TeamNotFoundError as e:
            raise service_errors.TeamNotFoundError("Failed to update team") from e

    async def delete_team(self, team_id: uuid.UUID) -> None:
        try:
            await self._team_repository.delete_team(team_id)
            await self._kafka_producer.send_team_deleted(team_id)
        except adapter_errors.TeamNotFoundError as e:
            raise service_errors.TeamNotFoundError("Failed to delete team") from e

    async def leave_team(self, team_id: uuid.UUID, user_id: uuid.UUID) -> None:
        try:
            team = await self._team_repository.get_team(team_id)
            
            if user_id not in team.member_ids:
                raise service_errors.UserNotFoundError(f"User {user_id} is not a member")
            
            if team.owner_id == user_id:
                raise service_errors.TeamOperationError("Owner cannot leave. Use delete_team instead.")
            
            await self._team_repository.remove_member(team_id, user_id)
            await self._kafka_producer.send_member_left(team_id, user_id, team.event_id)
        except adapter_errors.TeamNotFoundError as e:
            raise service_errors.TeamNotFoundError("Failed to leave team") from e

    async def kick_member(self, team_id: uuid.UUID, user_id: uuid.UUID) -> None:
        try:
            team = await self._team_repository.get_team(team_id)
            
            if user_id not in team.member_ids:
                raise service_errors.UserNotFoundError(f"User {user_id} is not a member")
            
            if team.owner_id == user_id:
                raise service_errors.TeamOperationError("Cannot kick team owner")
            
            await self._team_repository.kick_member(team_id, user_id)
            await self._kafka_producer.send_member_kicked(team_id, user_id, team.owner_id, team.event_id)
        except adapter_errors.TeamNotFoundError as e:
            raise service_errors.TeamNotFoundError("Failed to kick member") from e


    async def team_submit(self, team_id: uuid.UUID, submission_url: str) -> None:
        try:
            team = await self._team_repository.get_team(team_id)
            
            if team.status != TeamStatusEnum.FULL:
                raise service_errors.TeamOperationError(
                    f"Cannot submit. Team must be {TeamStatusEnum.FULL.value}."
                )
            
            await self._team_repository.team_submit(team_id, submission_url)
            await self._kafka_producer.send_team_submitted(team_id, submission_url, team.event_id, team.track_id)
        except adapter_errors.TeamNotFoundError as e:
            raise service_errors.TeamNotFoundError("Failed to submit team") from e

    async def change_team_status(self, team_id: uuid.UUID, status: TeamStatusEnum) -> None:
        try:
            await self._team_repository.change_team_status(team_id, status.value)
        except adapter_errors.TeamNotFoundError as e:
            raise service_errors.TeamNotFoundError("Failed to change status") from e