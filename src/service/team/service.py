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

    async def get_teams(self, team_id: uuid.UUID) -> Team:
        try:
            return await self._team_repository.get_team(team_id)
        except adapter_errors.TeamNotFoundError as e:
            raise service_errors.TeamNotFoundError("Failed to get team") from e

    async def create_team(self, team: Team) -> uuid.UUID:
        try:
            if team.owner.have_team:
                raise service_errors.ParticipantAlreadyInTeam(
                    "Participant already in team"
                )

            await self._team_repository.create_team(team)
            await self._kafka_producer.send_team_created(team)
            return team.id
        except adapter_errors.EventNotFoundError as e:
            raise service_errors.EventNotFoundError("Failed to find team") from e
        except adapter_errors.ParticipantNotFoundError as e:
            raise service_errors.ParticipantNotFoundError(
                "Failed to find member"
            ) from e
        except adapter_errors.TeamAlreadyExistsError as e:
            raise service_errors.TeamAlreadyExistsError("Team already exists") from e
        except adapter_errors.TrackNotFoundError as e:
            raise service_errors.TrackNotFoundError("Failed to find track") from e

    async def update_team(self, team: Team) -> None:
        try:
            await self._team_repository.update_team(team)
            await self._kafka_producer.send_team_updated(team)
        except adapter_errors.TeamNotFoundError as e:
            raise service_errors.TeamNotFoundError("Failed to update team") from e
        except adapter_errors.TrackNotFoundError as e:
            raise service_errors.TrackNotFoundError from e

    async def delete_team(self, team_id: uuid.UUID) -> None:
        try:
            team = await self._team_repository.get_team(team_id)
            await self._team_repository.delete_team(team_id)
            await self._kafka_producer.send_team_deleted(team)
        except adapter_errors.TeamNotFoundError as e:
            raise service_errors.TeamNotFoundError("Failed to delete team") from e

    async def leave_team(self, team_id: uuid.UUID, member_id: uuid.UUID) -> None:
        try:
            team = await self._team_repository.get_team(team_id)
            member = await self._team_repository.get_member_by_id(member_id)
            if member not in team.members:
                raise service_errors.ParticipantNotFoundError(
                    f"User {member.id} is not a member"
                )

            if team.owner == member:
                raise service_errors.TeamOperationError(
                    "Owner cannot leave. Use delete_team instead."
                )

            await self._team_repository.remove_member(team_id, member_id)
            await self._kafka_producer.send_member_left(team, member)
        except adapter_errors.TeamNotFoundError as e:
            raise service_errors.TeamNotFoundError("Failed to leave team") from e

    async def kick_member(self, team_id: uuid.UUID, member_id: uuid.UUID) -> None:
        try:
            team = await self._team_repository.get_team(team_id)
            member = await self._team_repository.get_member_by_id(member_id)

            if member not in team.members:
                raise service_errors.ParticipantNotFoundError(
                    f"User {member.id} is not a member"
                )

            if team.owner == member:
                raise service_errors.TeamOperationError("Cannot kick team owner")

            await self._team_repository.remove_member(team_id, member_id)
            await self._kafka_producer.send_member_kicked(team, member)
        except adapter_errors.TeamNotFoundError as e:
            raise service_errors.TeamNotFoundError("Failed to kick member") from e

    async def team_submit(self, team_id: uuid.UUID) -> None:
        try:
            team = await self._team_repository.get_team(team_id)
            if team.status in [
                TeamStatusEnum.DRAFT,
                TeamStatusEnum.SUBMITTED,
                TeamStatusEnum.CONFIRMED,
            ]:
                raise service_errors.TeamOperationError(
                    f"Cannot submit with {team.status}"
                )

            await self._team_repository.change_team_status(
                team_id, TeamStatusEnum.SUBMITTED
            )
            await self._kafka_producer.send_team_submitted(team)
        except adapter_errors.TeamNotFoundError as e:
            raise service_errors.TeamNotFoundError("Failed to submit team") from e

    async def change_team_status(
        self, team_id: uuid.UUID, status: TeamStatusEnum
    ) -> None:
        try:
            await self._team_repository.change_team_status(team_id, status)
        except adapter_errors.TeamNotFoundError as e:
            raise service_errors.TeamNotFoundError("Failed to change status") from e
