import uuid

import src.adapters.repository.errors as adapter_errors
import src.service.errors as service_errors
from src.models.invitation import Invitation, JoinRequest
from src.service.invitation.protocols import InvitationRepository, KafkaProducer


class InvitationService:
    def __init__(
        self,
        invitation_repository: InvitationRepository,
        kafka_producer: KafkaProducer,
    ) -> None:
        self._repository = invitation_repository
        self._kafka_producer = kafka_producer

    async def create_invitation(self, invitation: Invitation) -> uuid.UUID:
        """Captain invites a user into the team.

        Raises:
            TeamNotFoundError
            ParticipantNotFoundError
            RoleNotFoundError
            InvitationAlreadyExistsError
            ParticipantAlreadyInTeam
        """
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
        return invitation.id

    async def get_invitation(self, invitation_id: uuid.UUID) -> Invitation:
        try:
            return await self._repository.get_invitation(invitation_id)
        except adapter_errors.InvitationNotFoundError as e:
            raise service_errors.InvitationNotFoundError("Invitation not found") from e
        except adapter_errors.TeamNotFoundError as e:
            raise service_errors.TeamNotFoundError("Team not found") from e
        except adapter_errors.ParticipantNotFoundError as e:
            raise service_errors.ParticipantNotFoundError(
                "Participant not found"
            ) from e
        except adapter_errors.RoleNotFoundError as e:
            raise service_errors.RoleNotFoundError("Role not found") from e

    async def get_invitations_by_team(self, team_id: uuid.UUID) -> list[Invitation]:
        try:
            return await self._repository.get_invitations_by_team(team_id)
        except adapter_errors.TeamNotFoundError as e:
            raise service_errors.TeamNotFoundError("Team not found") from e

    async def cancel_invitation(self, invitation_id: uuid.UUID) -> None:
        """Captain cancels (deletes) his invitation."""
        try:
            invitation = await self._repository.get_invitation(invitation_id)
            await self._repository.delete_invitation(invitation_id)
        except adapter_errors.InvitationNotFoundError as e:
            raise service_errors.InvitationNotFoundError("Invitation not found") from e

        await self._kafka_producer.send_invitation_canceled(invitation)

    async def accept_invitation(self, invitation_id: uuid.UUID) -> None:
        """User accepts invitation; he is added to the team."""
        try:
            invitation = await self._repository.accept_invitation(invitation_id)
        except adapter_errors.InvitationNotFoundError as e:
            raise service_errors.InvitationNotFoundError("Invitation not found") from e
        except adapter_errors.ParticipantAlreadyInTeamError as e:
            raise service_errors.ParticipantAlreadyInTeam(
                "Participant already in a team"
            ) from e

        await self._kafka_producer.send_invitation_accepted(invitation)

    async def reject_invitation(self, invitation_id: uuid.UUID) -> None:
        """User rejects invitation."""
        try:
            invitation = await self._repository.get_invitation(invitation_id)
            await self._repository.delete_invitation(invitation_id)
        except adapter_errors.InvitationNotFoundError as e:
            raise service_errors.InvitationNotFoundError("Invitation not found") from e

        await self._kafka_producer.send_invitation_rejected(invitation)

    async def create_join_request(self, join_request: JoinRequest) -> uuid.UUID:
        """User requests to join team."""
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
        return join_request.id

    async def get_join_request(self, join_request_id: uuid.UUID) -> JoinRequest:
        try:
            return await self._repository.get_join_request(join_request_id)
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

    async def get_join_requests_for_member(
        self, track_id: uuid.UUID, member_id: uuid.UUID
    ) -> list[JoinRequest]:
        return await self._repository.get_join_requests_by_track_and_member(
            track_id, member_id
        )

    async def cancel_join_request(self, join_request_id: uuid.UUID) -> None:
        """User cancels his own join request."""
        try:
            join_request = await self._repository.get_join_request(join_request_id)
            await self._repository.delete_join_request(join_request_id)
        except adapter_errors.JoinRequestNotFoundError as e:
            raise service_errors.JoinRequestNotFoundError(
                "JoinRequest not found"
            ) from e

        await self._kafka_producer.send_join_request_canceled(join_request)

    async def accept_join_request(self, join_request_id: uuid.UUID) -> None:
        """Captain accepts join request, user becomes a team member."""
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

    async def reject_join_request(self, join_request_id: uuid.UUID) -> None:
        """Captain rejects join request."""
        try:
            join_request = await self._repository.get_join_request(join_request_id)
            await self._repository.delete_join_request(join_request_id)
        except adapter_errors.JoinRequestNotFoundError as e:
            raise service_errors.JoinRequestNotFoundError(
                "JoinRequest not found"
            ) from e

        await self._kafka_producer.send_join_request_rejected(join_request)
