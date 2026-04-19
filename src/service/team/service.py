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

    async def create_team(self, team: Team) -> uuid.UUID:
        try:
            owner = await self._team_repository.get_member_by_id(
                team.owner.id, team.event_id
            )
            if owner.have_team:
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
                "Failed to find team's owner"
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
            member = await self._team_repository.get_member_by_id(
                member_id, team.event_id
            )
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
        except adapter_errors.ParticipantNotFoundError as e:
            raise service_errors.ParticipantNotFoundError(
                "Failed to find member"
            ) from e

    async def kick_member(self, team_id: uuid.UUID, member_id: uuid.UUID) -> None:
        try:
            team = await self._team_repository.get_team(team_id)
            member = await self._team_repository.get_member_by_id(
                member_id, team.event_id
            )

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
        except adapter_errors.ParticipantNotFoundError as e:
            raise service_errors.ParticipantNotFoundError(
                "Failed to find member"
            ) from e

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

    async def get_teams_by_event_id(self, event_id: uuid.UUID) -> list[Team]:
        try:
            all_teams = await self._team_repository.get_all_teams()
            teams = [team for team in all_teams if team.event_id == event_id]

            if not teams:
                raise service_errors.EventNotFoundError(
                    f"No teams found for event {event_id}"
                )

            return teams
        except adapter_errors.EventNotFoundError:
            raise service_errors.EventNotFoundError(f"Event {event_id} not found")

    async def get_teams_by_user(self, user_id: uuid.UUID) -> list[Team]:
        try:
            all_teams = await self._team_repository.get_all_teams()
            result = []
            for team in all_teams:
                if team.owner.id == user_id:
                    result.append(team)
                elif any(member.id == user_id for member in team.members):
                    result.append(team)
            return result
        except adapter_errors.ParticipantNotFoundError:
            raise service_errors.EventNotFoundError(f"Event {user_id} not found")

    async def get_user_team_in_event(
        self, user_id: uuid.UUID, event_id: uuid.UUID
    ) -> Team | None:
        try:
            all_teams = await self._team_repository.get_all_teams()
            event_teams = [team for team in all_teams if team.event_id == event_id]
            if not event_teams:
                raise service_errors.EventNotFoundError(f"Event {event_id} not found")

            for team in event_teams:
                if team.owner.id == user_id:
                    return team
                if any(member.id == user_id for member in team.members):
                    return team
            return None
        except adapter_errors.EventNotFoundError:
            raise service_errors.EventNotFoundError(f"Event {event_id} not found")
        except adapter_errors.ParticipantNotFoundError:
            raise service_errors.EventNotFoundError(f"Event {user_id} not found")
