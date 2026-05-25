from loguru import logger
from opentelemetry import trace
import uuid

from src.service.invitation.protocols import InvitationRepository, KafkaProducer
from src.models.invitation import Invitation, JoinRequest
from src.service.tracing import trace_business_logic
import src.adapters.repository.errors as adapter_errors
import src.service.errors as service_errors

tracer = trace.get_tracer(__name__)


class InvitationService:
    def __init__(
        self,
        invitation_repository: InvitationRepository,
        kafka_producer: KafkaProducer,
    ) -> None:
        self._repository = invitation_repository
        self._kafka_producer = kafka_producer

    @trace_business_logic("invitation_service")
    async def create_invitation(self, invitation: Invitation) -> uuid.UUID:
        """Captain invites a user into the team.

        Raises:
            TeamNotFoundError
            ParticipantNotFoundError
            RoleNotFoundError
            InvitationAlreadyExistsError
            ParticipantAlreadyInTeam
        """
        span = trace.get_current_span()
        span.set_attribute("invitation.id", str(invitation.id))
        span.set_attribute("team.id", str(invitation.team_id))
        span.set_attribute("member.id", str(invitation.member.id))

        logger.info(
            "service_creating_invitation",
            invitation_id=str(invitation.id),
            team_id=str(invitation.team_id),
            member_id=str(invitation.member.id),
        )

        if invitation.member.have_team:
            raise service_errors.ParticipantAlreadyInTeam(
                f"Participant {invitation.member.id} already in a team"
            )

        try:
            await self._repository.create_invitation(invitation)
        except adapter_errors.TeamNotFoundError as e:
            raise service_errors.TeamNotFoundError("Team not found") from e
        except adapter_errors.ParticipantNotFoundError as e:
            raise service_errors.ParticipantNotFoundError(
                "Participant not found"
            ) from e
        except adapter_errors.RoleNotFoundError as e:
            raise service_errors.RoleNotFoundError("Role not found") from e
        except adapter_errors.InvitationAlreadyExistsError as e:
            raise service_errors.InvitationAlreadyExistsError(
                "Invitation already exists"
            ) from e

        await self._kafka_producer.send_invitation_created(invitation)
        logger.info(
            "service_invitation_created",
            invitation_id=str(invitation.id),
        )
        return invitation.id

    @trace_business_logic("invitation_service")
    async def get_invitation(self, invitation_id: uuid.UUID) -> Invitation:
        span = trace.get_current_span()
        span.set_attribute("invitation.id", str(invitation_id))

        logger.info("service_receiving_invitation",
                    invitation_id=str(invitation_id))

        try:
            invitation = await self._repository.get_invitation(invitation_id)
            logger.info(
                "service_invitation_received", invitation_id=str(invitation_id)
            )
            return invitation
        except adapter_errors.InvitationNotFoundError as e:
            raise service_errors.InvitationNotFoundError(
                "Invitation not found") from e
        except adapter_errors.TeamNotFoundError as e:
            raise service_errors.TeamNotFoundError("Team not found") from e
        except adapter_errors.ParticipantNotFoundError as e:
            raise service_errors.ParticipantNotFoundError(
                "Participant not found"
            ) from e
        except adapter_errors.RoleNotFoundError as e:
            raise service_errors.RoleNotFoundError("Role not found") from e

    @trace_business_logic("invitation_service")
    async def get_invitations_by_team(self, team_id: uuid.UUID) -> list[Invitation]:
        span = trace.get_current_span()
        span.set_attribute("team.id", str(team_id))

        logger.info("service_receiving_invitations_by_team",
                    team_id=str(team_id))

        try:
            invitations = await self._repository.get_invitations_by_team(team_id)
            logger.info(
                "service_invitations_received",
                team_id=str(team_id),
                count=len(invitations),
            )
            return invitations
        except adapter_errors.TeamNotFoundError as e:
            raise service_errors.TeamNotFoundError("Team not found") from e

    @trace_business_logic("invitation_service")
    async def cancel_invitation(self, invitation_id: uuid.UUID) -> None:
        """Captain cancels (deletes) his invitation."""
        span = trace.get_current_span()
        span.set_attribute("invitation.id", str(invitation_id))

        logger.info("service_canceling_invitation",
                    invitation_id=str(invitation_id))

        try:
            invitation = await self._repository.get_invitation(invitation_id)
            await self._repository.delete_invitation(invitation_id)
        except adapter_errors.InvitationNotFoundError as e:
            raise service_errors.InvitationNotFoundError(
                "Invitation not found") from e

        await self._kafka_producer.send_invitation_canceled(invitation)
        logger.info("service_invitation_canceled",
                    invitation_id=str(invitation_id))

    @trace_business_logic("invitation_service")
    async def accept_invitation(self, invitation_id: uuid.UUID) -> None:
        """User accepts invitation; he is added to the team."""
        span = trace.get_current_span()
        span.set_attribute("invitation.id", str(invitation_id))

        logger.info("service_accepting_invitation",
                    invitation_id=str(invitation_id))

        try:
            invitation = await self._repository.accept_invitation(invitation_id)
        except adapter_errors.InvitationNotFoundError as e:
            raise service_errors.InvitationNotFoundError(
                "Invitation not found") from e
        except adapter_errors.ParticipantAlreadyInTeamError as e:
            raise service_errors.ParticipantAlreadyInTeam(
                "Participant already in a team"
            ) from e

        await self._kafka_producer.send_invitation_accepted(invitation)
        logger.info("service_invitation_accepted",
                    invitation_id=str(invitation_id))

    @trace_business_logic("invitation_service")
    async def reject_invitation(self, invitation_id: uuid.UUID) -> None:
        """User rejects invitation."""
        span = trace.get_current_span()
        span.set_attribute("invitation.id", str(invitation_id))

        logger.info("service_rejecting_invitation",
                    invitation_id=str(invitation_id))

        try:
            invitation = await self._repository.get_invitation(invitation_id)
            await self._repository.delete_invitation(invitation_id)
        except adapter_errors.InvitationNotFoundError as e:
            raise service_errors.InvitationNotFoundError(
                "Invitation not found") from e

        await self._kafka_producer.send_invitation_rejected(invitation)
        logger.info("service_invitation_rejected",
                    invitation_id=str(invitation_id))

    @trace_business_logic("invitation_service")
    async def create_join_request(self, join_request: JoinRequest) -> uuid.UUID:
        """User requests to join team."""
        span = trace.get_current_span()
        span.set_attribute("join_request.id", str(join_request.id))
        span.set_attribute("team.id", str(join_request.team_id))
        span.set_attribute("member.id", str(join_request.member.id))

        logger.info(
            "service_creating_join_request",
            join_request_id=str(join_request.id),
            team_id=str(join_request.team_id),
            member_id=str(join_request.member.id),
        )

        if join_request.member.have_team:
            raise service_errors.ParticipantAlreadyInTeam(
                f"Participant {join_request.member.id} already in a team"
            )

        try:
            await self._repository.create_join_request(join_request)
        except adapter_errors.TeamNotFoundError as e:
            raise service_errors.TeamNotFoundError("Team not found") from e
        except adapter_errors.ParticipantNotFoundError as e:
            raise service_errors.ParticipantNotFoundError(
                "Participant not found"
            ) from e
        except adapter_errors.RoleNotFoundError as e:
            raise service_errors.RoleNotFoundError("Role not found") from e
        except adapter_errors.JoinRequestAlreadyExistsError as e:
            raise service_errors.JoinRequestAlreadyExistsError(
                "JoinRequest already exists"
            ) from e

        await self._kafka_producer.send_join_request_created(join_request)
        logger.info(
            "service_join_request_created",
            join_request_id=str(join_request.id),
        )
        return join_request.id

    @trace_business_logic("invitation_service")
    async def get_join_request(self, join_request_id: uuid.UUID) -> JoinRequest:
        span = trace.get_current_span()
        span.set_attribute("join_request.id", str(join_request_id))

        logger.info(
            "service_receiving_join_request", join_request_id=str(join_request_id)
        )

        try:
            jr = await self._repository.get_join_request(join_request_id)
            logger.info(
                "service_join_request_received",
                join_request_id=str(join_request_id),
            )
            return jr
        except adapter_errors.JoinRequestNotFoundError as e:
            raise service_errors.JoinRequestNotFoundError(
                "JoinRequest not found"
            ) from e
        except adapter_errors.TeamNotFoundError as e:
            raise service_errors.TeamNotFoundError("Team not found") from e
        except adapter_errors.ParticipantNotFoundError as e:
            raise service_errors.ParticipantNotFoundError(
                "Participant not found"
            ) from e
        except adapter_errors.RoleNotFoundError as e:
            raise service_errors.RoleNotFoundError("Role not found") from e

    @trace_business_logic("invitation_service")
    async def get_join_requests_for_member(
        self, track_id: uuid.UUID, member_id: uuid.UUID
    ) -> list[JoinRequest]:
        span = trace.get_current_span()
        span.set_attribute("track.id", str(track_id))
        span.set_attribute("member.id", str(member_id))

        logger.info(
            "service_receiving_join_requests_for_member",
            track_id=str(track_id),
            member_id=str(member_id),
        )

        join_requests = await self._repository.get_join_requests_by_track_and_member(
            track_id, member_id
        )

        logger.info(
            "service_join_requests_received",
            track_id=str(track_id),
            member_id=str(member_id),
            count=len(join_requests),
        )
        return join_requests

    @trace_business_logic("invitation_service")
    async def cancel_join_request(self, join_request_id: uuid.UUID) -> None:
        """User cancels his own join request."""
        span = trace.get_current_span()
        span.set_attribute("join_request.id", str(join_request_id))

        logger.info(
            "service_canceling_join_request", join_request_id=str(join_request_id)
        )

        try:
            join_request = await self._repository.get_join_request(join_request_id)
            await self._repository.delete_join_request(join_request_id)
        except adapter_errors.JoinRequestNotFoundError as e:
            raise service_errors.JoinRequestNotFoundError(
                "JoinRequest not found"
            ) from e

        await self._kafka_producer.send_join_request_canceled(join_request)
        logger.info(
            "service_join_request_canceled", join_request_id=str(join_request_id)
        )

    @trace_business_logic("invitation_service")
    async def accept_join_request(self, join_request_id: uuid.UUID) -> None:
        """Captain accepts join request, user becomes a team member."""
        span = trace.get_current_span()
        span.set_attribute("join_request.id", str(join_request_id))

        logger.info(
            "service_accepting_join_request", join_request_id=str(join_request_id)
        )

        try:
            join_request = await self._repository.accept_join_request(join_request_id)
        except adapter_errors.JoinRequestNotFoundError as e:
            raise service_errors.JoinRequestNotFoundError(
                "JoinRequest not found"
            ) from e
        except adapter_errors.ParticipantAlreadyInTeamError as e:
            raise service_errors.ParticipantAlreadyInTeam(
                "Participant already in a team"
            ) from e

        await self._kafka_producer.send_join_request_accepted(join_request)
        logger.info(
            "service_join_request_accepted", join_request_id=str(join_request_id)
        )

    @trace_business_logic("invitation_service")
    async def reject_join_request(self, join_request_id: uuid.UUID) -> None:
        """Captain rejects join request."""
        span = trace.get_current_span()
        span.set_attribute("join_request.id", str(join_request_id))

        logger.info(
            "service_rejecting_join_request", join_request_id=str(join_request_id)
        )

        try:
            join_request = await self._repository.get_join_request(join_request_id)
            await self._repository.delete_join_request(join_request_id)
        except adapter_errors.JoinRequestNotFoundError as e:
            raise service_errors.JoinRequestNotFoundError(
                "JoinRequest not found"
            ) from e

        await self._kafka_producer.send_join_request_rejected(join_request)
        logger.info(
            "service_join_request_rejected", join_request_id=str(join_request_id)
        )
