from loguru import logger
from opentelemetry import trace
import uuid

from src.service.team.protocols import TeamRepository, KafkaProducer
from src.models.team import Team, TeamStatusEnum
from src.service.tracing import trace_business_logic
import src.adapters.repository.errors as adapter_errors
import src.service.errors as service_errors

tracer = trace.get_tracer(__name__)


class TeamService:
    def __init__(
        self,
        team_repository: TeamRepository,
        kafka_producer: KafkaProducer,
    ) -> None:
        self._team_repository = team_repository
        self._kafka_producer = kafka_producer

    @trace_business_logic("team_service")
    async def get_team(self, team_id: uuid.UUID) -> Team:
        span = trace.get_current_span()
        span.set_attribute("team.id", str(team_id))

        logger.info("service_receiving_team", team_id=str(team_id))

        try:
            team = await self._team_repository.get_team(team_id)
            logger.info("service_team_received", team_id=str(team_id))
            return team
        except adapter_errors.TeamNotFoundError as e:
            logger.warning(
                "service_team_get_not_found", team_id=str(team_id), error=str(e)
            )
            raise service_errors.TeamNotFoundError("Failed to get team") from e

    @trace_business_logic("team_service")
    async def create_team(self, team: Team) -> uuid.UUID:
        span = trace.get_current_span()
        span.set_attribute("team.id", str(team.id))
        span.set_attribute("event.id", str(team.event_id))
        span.set_attribute("team.owner_id", str(team.owner.id))

        logger.info(
            "service_creating_team",
            team_id=str(team.id),
            event_id=str(team.event_id),
            owner_id=str(team.owner.id),
        )

        try:
            owner = await self._team_repository.get_member_by_id(
                team.owner.id, team.event_id
            )
            if owner.have_team:
                logger.warning(
                    "service_team_owner_already_in_team",
                    team_id=str(team.id),
                    owner_id=str(team.owner.id),
                )
                raise service_errors.ParticipantAlreadyInTeam(
                    "Participant already in team"
                )

            await self._team_repository.create_team(team)
            await self._kafka_producer.send_team_created(team)
            logger.info("service_team_created", team_id=str(team.id))
            return team.id
        except adapter_errors.EventNotFoundError as e:
            logger.warning(
                "service_team_create_event_not_found",
                team_id=str(team.id),
                event_id=str(team.event_id),
                error=str(e),
            )
            raise service_errors.EventNotFoundError("Failed to find team") from e
        except adapter_errors.ParticipantNotFoundError as e:
            logger.warning(
                "service_team_create_owner_not_found",
                team_id=str(team.id),
                owner_id=str(team.owner.id),
                error=str(e),
            )
            raise service_errors.ParticipantNotFoundError(
                "Failed to find team's owner"
            ) from e
        except adapter_errors.TeamAlreadyExistsError as e:
            logger.warning(
                "service_team_already_exists",
                team_id=str(team.id),
                error=str(e),
            )
            raise service_errors.TeamAlreadyExistsError("Team already exists") from e
        except adapter_errors.TrackNotFoundError as e:
            logger.warning(
                "service_team_create_track_not_found",
                team_id=str(team.id),
                error=str(e),
            )
            raise service_errors.TrackNotFoundError("Failed to find track") from e

    @trace_business_logic("team_service")
    async def update_team(self, team: Team) -> None:
        span = trace.get_current_span()
        span.set_attribute("team.id", str(team.id))

        logger.info("service_updating_team", team_id=str(team.id))

        try:
            await self._team_repository.update_team(team)
            await self._kafka_producer.send_team_updated(team)
            logger.info("service_team_updated", team_id=str(team.id))
        except adapter_errors.TeamNotFoundError as e:
            logger.warning(
                "service_team_update_not_found",
                team_id=str(team.id),
                error=str(e),
            )
            raise service_errors.TeamNotFoundError("Failed to update team") from e
        except adapter_errors.TrackNotFoundError as e:
            logger.warning(
                "service_team_update_track_not_found",
                team_id=str(team.id),
                error=str(e),
            )
            raise service_errors.TrackNotFoundError from e

    @trace_business_logic("team_service")
    async def delete_team(self, team_id: uuid.UUID) -> None:
        span = trace.get_current_span()
        span.set_attribute("team.id", str(team_id))

        logger.info("service_deleting_team", team_id=str(team_id))

        try:
            team = await self._team_repository.get_team(team_id)
            await self._team_repository.delete_team(team_id)
            await self._kafka_producer.send_team_deleted(team)
            logger.info("service_team_deleted", team_id=str(team_id))
        except adapter_errors.TeamNotFoundError as e:
            logger.warning(
                "service_team_delete_not_found",
                team_id=str(team_id),
                error=str(e),
            )
            raise service_errors.TeamNotFoundError("Failed to delete team") from e

    @trace_business_logic("team_service")
    async def leave_team(self, team_id: uuid.UUID, member_id: uuid.UUID) -> None:
        span = trace.get_current_span()
        span.set_attribute("team.id", str(team_id))
        span.set_attribute("member.id", str(member_id))

        logger.info(
            "service_leaving_team",
            team_id=str(team_id),
            member_id=str(member_id),
        )

        try:
            team = await self._team_repository.get_team(team_id)
            member = await self._team_repository.get_member_by_id(
                member_id, team.event_id
            )
            if member not in team.members:
                logger.warning(
                    "service_leave_team_not_a_member",
                    team_id=str(team_id),
                    member_id=str(member_id),
                )
                raise service_errors.ParticipantNotFoundError(
                    f"User {member.id} is not a member"
                )

            if team.owner == member:
                logger.warning(
                    "service_leave_team_owner_cannot_leave",
                    team_id=str(team_id),
                    member_id=str(member_id),
                )
                raise service_errors.TeamOperationError(
                    "Owner cannot leave. Use delete_team instead."
                )

            await self._team_repository.remove_member(team_id, member_id)
            await self._kafka_producer.send_member_left(team, member)
            logger.info(
                "service_member_left_team",
                team_id=str(team_id),
                member_id=str(member_id),
            )
        except adapter_errors.TeamNotFoundError as e:
            logger.warning(
                "service_leave_team_not_found",
                team_id=str(team_id),
                member_id=str(member_id),
                error=str(e),
            )
            raise service_errors.TeamNotFoundError("Failed to leave team") from e
        except adapter_errors.ParticipantNotFoundError as e:
            logger.warning(
                "service_leave_team_member_not_found",
                team_id=str(team_id),
                member_id=str(member_id),
                error=str(e),
            )
            raise service_errors.ParticipantNotFoundError(
                "Failed to find member"
            ) from e

    @trace_business_logic("team_service")
    async def kick_member(self, team_id: uuid.UUID, member_id: uuid.UUID) -> None:
        span = trace.get_current_span()
        span.set_attribute("team.id", str(team_id))
        span.set_attribute("member.id", str(member_id))

        logger.info(
            "service_kicking_member",
            team_id=str(team_id),
            member_id=str(member_id),
        )

        try:
            team = await self._team_repository.get_team(team_id)
            member = await self._team_repository.get_member_by_id(
                member_id, team.event_id
            )

            if member not in team.members:
                logger.warning(
                    "service_kick_member_not_a_member",
                    team_id=str(team_id),
                    member_id=str(member_id),
                )
                raise service_errors.ParticipantNotFoundError(
                    f"User {member.id} is not a member"
                )

            if team.owner == member:
                logger.warning(
                    "service_kick_member_cannot_kick_owner",
                    team_id=str(team_id),
                    member_id=str(member_id),
                )
                raise service_errors.TeamOperationError("Cannot kick team owner")

            await self._team_repository.remove_member(team_id, member_id)
            await self._kafka_producer.send_member_kicked(team, member)
            logger.info(
                "service_member_kicked",
                team_id=str(team_id),
                member_id=str(member_id),
            )
        except adapter_errors.TeamNotFoundError as e:
            logger.warning(
                "service_kick_member_team_not_found",
                team_id=str(team_id),
                member_id=str(member_id),
                error=str(e),
            )
            raise service_errors.TeamNotFoundError("Failed to kick member") from e
        except adapter_errors.ParticipantNotFoundError as e:
            logger.warning(
                "service_kick_member_not_found",
                team_id=str(team_id),
                member_id=str(member_id),
                error=str(e),
            )
            raise service_errors.ParticipantNotFoundError(
                "Failed to find member"
            ) from e

    @trace_business_logic("team_service")
    async def change_member_role(
        self,
        team_id: uuid.UUID,
        member_id: uuid.UUID,
        new_role_id: uuid.UUID,
    ) -> None:
        span = trace.get_current_span()
        span.set_attribute("team.id", str(team_id))
        span.set_attribute("member.id", str(member_id))
        span.set_attribute("role.id", str(new_role_id))

        logger.info(
            "service_changing_member_role",
            team_id=str(team_id),
            member_id=str(member_id),
            new_role_id=str(new_role_id),
        )

        try:
            previous_role_id = await self._team_repository.change_member_role(
                team_id, member_id, new_role_id
            )
            team = await self._team_repository.get_team(team_id)
            if str(team.owner.id) == str(member_id):
                member = team.owner
            else:
                member = next(
                    (m for m in team.members if str(m.id) == str(member_id)),
                    None,
                )
            if member is None:
                raise service_errors.ParticipantNotFoundError(
                    f"Member {member_id} not found in team {team_id}"
                )
            await self._kafka_producer.send_member_role_changed(
                team, member, previous_role_id
            )
            logger.info(
                "service_member_role_changed",
                team_id=str(team_id),
                member_id=str(member_id),
            )
        except adapter_errors.TeamNotFoundError as e:
            logger.warning(
                "service_change_member_role_team_not_found",
                team_id=str(team_id),
                error=str(e),
            )
            raise service_errors.TeamNotFoundError(
                "Failed to change member role"
            ) from e
        except adapter_errors.ParticipantNotFoundError as e:
            logger.warning(
                "service_change_member_role_member_not_found",
                team_id=str(team_id),
                member_id=str(member_id),
                error=str(e),
            )
            raise service_errors.ParticipantNotFoundError(
                "Failed to find member"
            ) from e

    @trace_business_logic("team_service")
    async def team_submit(self, team_id: uuid.UUID) -> None:
        span = trace.get_current_span()
        span.set_attribute("team.id", str(team_id))

        logger.info("service_submitting_team", team_id=str(team_id))

        try:
            team = await self._team_repository.get_team(team_id)
            if team.status in [
                TeamStatusEnum.DRAFT,
                TeamStatusEnum.SUBMITTED,
                TeamStatusEnum.CONFIRMED,
            ]:
                logger.warning(
                    "service_team_submit_invalid_status",
                    team_id=str(team_id),
                    status=str(team.status),
                )
                raise service_errors.TeamOperationError(
                    f"Cannot submit with {team.status}"
                )

            await self._team_repository.change_team_status(
                team_id, TeamStatusEnum.SUBMITTED
            )
            await self._kafka_producer.send_team_submitted(team)
            logger.info("service_team_submitted", team_id=str(team_id))
        except adapter_errors.TeamNotFoundError as e:
            logger.warning(
                "service_team_submit_not_found",
                team_id=str(team_id),
                error=str(e),
            )
            raise service_errors.TeamNotFoundError("Failed to submit team") from e

    @trace_business_logic("team_service")
    async def change_team_status(
        self, team_id: uuid.UUID, status: TeamStatusEnum
    ) -> None:
        span = trace.get_current_span()
        span.set_attribute("team.id", str(team_id))
        span.set_attribute("team.status", str(status))

        logger.info(
            "service_changing_team_status",
            team_id=str(team_id),
            status=str(status),
        )

        try:
            await self._team_repository.change_team_status(team_id, status)
            logger.info(
                "service_team_status_changed",
                team_id=str(team_id),
                status=str(status),
            )
        except adapter_errors.TeamNotFoundError as e:
            logger.warning(
                "service_team_change_status_not_found",
                team_id=str(team_id),
                status=str(status),
                error=str(e),
            )
            raise service_errors.TeamNotFoundError("Failed to change status") from e

    @trace_business_logic("team_service")
    async def get_teams_by_event_id(self, event_id: uuid.UUID) -> list[Team]:
        span = trace.get_current_span()
        span.set_attribute("event.id", str(event_id))

        logger.info("service_receiving_teams_by_event", event_id=str(event_id))

        try:
            teams = await self._team_repository.get_teams_by_event_id(event_id)
            logger.info(
                "service_teams_received",
                event_id=str(event_id),
                count=len(teams),
            )
            return teams
        except adapter_errors.EventNotFoundError as e:
            logger.warning(
                "service_teams_by_event_not_found",
                event_id=str(event_id),
                error=str(e),
            )
            raise service_errors.EventNotFoundError(
                f"Event {event_id} not found"
            ) from e

    @trace_business_logic("team_service")
    async def get_teams_by_user(self, user_id: uuid.UUID) -> list[Team]:
        span = trace.get_current_span()
        span.set_attribute("user.id", str(user_id))

        logger.info("service_receiving_teams_by_user", user_id=str(user_id))

        try:
            teams = await self._team_repository.get_teams_by_user_id(user_id)
            logger.info(
                "service_user_teams_received",
                user_id=str(user_id),
                count=len(teams),
            )
            return teams
        except adapter_errors.ParticipantNotFoundError as e:
            logger.warning(
                "service_teams_by_user_not_found",
                user_id=str(user_id),
                error=str(e),
            )
            raise service_errors.ParticipantNotFoundError(
                f"User {user_id} not found"
            ) from e

    @trace_business_logic("team_service")
    async def get_user_team_in_event(
        self, user_id: uuid.UUID, event_id: uuid.UUID
    ) -> Team | None:
        span = trace.get_current_span()
        span.set_attribute("user.id", str(user_id))
        span.set_attribute("event.id", str(event_id))

        logger.info(
            "service_receiving_user_team_in_event",
            user_id=str(user_id),
            event_id=str(event_id),
        )

        try:
            team = await self._team_repository.get_user_team_in_event(user_id, event_id)
            logger.info(
                "service_user_team_in_event_received",
                user_id=str(user_id),
                event_id=str(event_id),
                found=team is not None,
            )
            return team
        except adapter_errors.EventNotFoundError as e:
            logger.warning(
                "service_user_team_in_event_event_not_found",
                user_id=str(user_id),
                event_id=str(event_id),
                error=str(e),
            )
            raise service_errors.EventNotFoundError(
                f"Event {event_id} not found"
            ) from e
        except adapter_errors.ParticipantNotFoundError as e:
            logger.warning(
                "service_user_team_in_event_user_not_found",
                user_id=str(user_id),
                event_id=str(event_id),
                error=str(e),
            )
            raise service_errors.ParticipantNotFoundError(
                f"User {user_id} not found"
            ) from e
