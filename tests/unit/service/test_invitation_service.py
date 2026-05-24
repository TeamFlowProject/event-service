import uuid
from unittest.mock import AsyncMock

import pytest

import src.adapters.repository.errors as adapter_errors
import src.service.errors as service_errors
from src.models.event import Participant
from src.models.invitation import Invitation, JoinRequest
from src.models.track import Role
from src.service.invitation.service import InvitationService


def make_participant(**kwargs) -> Participant:
    defaults = dict(
        id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        name="Alice",
        surname="Smith",
        patronymic="Doe",
        have_team=False,
        role_id=None,
    )
    defaults.update(kwargs)
    return Participant(**defaults)  # type: ignore


def make_role(**kwargs) -> Role:
    defaults = dict(
        id=uuid.uuid4(),
        track_id=uuid.uuid4(),
        name="Developer",
        description="Dev role",
        count=3,
    )
    defaults.update(kwargs)
    return Role(**defaults)  # type: ignore


def make_invitation(**kwargs) -> Invitation:
    defaults = dict(
        id=uuid.uuid4(),
        team_id=uuid.uuid4(),
        owner=make_participant(),
        member=make_participant(),
        role=make_role(),
        description="please join",
    )
    defaults.update(kwargs)
    return Invitation(**defaults)  # type: ignore


def make_join_request(**kwargs) -> JoinRequest:
    defaults = dict(
        id=uuid.uuid4(),
        team_id=uuid.uuid4(),
        owner=make_participant(),
        member=make_participant(),
        role=make_role(),
        description="may I join?",
    )
    defaults.update(kwargs)
    return JoinRequest(**defaults)  # type: ignore


@pytest.fixture
def repo():
    return AsyncMock()


@pytest.fixture
def kafka():
    return AsyncMock()


@pytest.fixture
def service(repo, kafka):
    return InvitationService(invitation_repository=repo, kafka_producer=kafka)


@pytest.mark.unit
class TestCreateInvitation:
    @pytest.mark.asyncio
    async def test_returns_id_and_sends_kafka(self, service, repo, kafka):
        invitation = make_invitation()

        result = await service.create_invitation(invitation)

        assert result == invitation.id
        repo.create_invitation.assert_awaited_once_with(invitation)
        kafka.send_invitation_created.assert_awaited_once_with(invitation)

    @pytest.mark.asyncio
    async def test_raises_already_in_team(self, service, repo, kafka):
        invitation = make_invitation(member=make_participant(have_team=True))

        with pytest.raises(service_errors.ParticipantAlreadyInTeam):
            await service.create_invitation(invitation)

        repo.create_invitation.assert_not_called()
        kafka.send_invitation_created.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_team_not_found(self, service, repo, kafka):
        repo.create_invitation.side_effect = adapter_errors.TeamNotFoundError

        with pytest.raises(service_errors.TeamNotFoundError):
            await service.create_invitation(make_invitation())

        kafka.send_invitation_created.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_participant_not_found(self, service, repo):
        repo.create_invitation.side_effect = adapter_errors.ParticipantNotFoundError

        with pytest.raises(service_errors.ParticipantNotFoundError):
            await service.create_invitation(make_invitation())

    @pytest.mark.asyncio
    async def test_raises_role_not_found(self, service, repo):
        repo.create_invitation.side_effect = adapter_errors.RoleNotFoundError

        with pytest.raises(service_errors.RoleNotFoundError):
            await service.create_invitation(make_invitation())

    @pytest.mark.asyncio
    async def test_raises_already_exists(self, service, repo):
        repo.create_invitation.side_effect = adapter_errors.InvitationAlreadyExistsError

        with pytest.raises(service_errors.InvitationAlreadyExistsError):
            await service.create_invitation(make_invitation())


@pytest.mark.unit
class TestGetInvitation:
    @pytest.mark.asyncio
    async def test_returns_invitation(self, service, repo):
        invitation = make_invitation()
        repo.get_invitation.return_value = invitation

        result = await service.get_invitation(invitation.id)

        assert result == invitation

    @pytest.mark.asyncio
    async def test_raises_when_not_found(self, service, repo):
        repo.get_invitation.side_effect = adapter_errors.InvitationNotFoundError

        with pytest.raises(service_errors.InvitationNotFoundError):
            await service.get_invitation(uuid.uuid4())


@pytest.mark.unit
class TestGetInvitationsByTeam:
    @pytest.mark.asyncio
    async def test_returns_list(self, service, repo):
        invitations = [make_invitation(), make_invitation()]
        repo.get_invitations_by_team.return_value = invitations

        result = await service.get_invitations_by_team(uuid.uuid4())

        assert result == invitations

    @pytest.mark.asyncio
    async def test_raises_team_not_found(self, service, repo):
        repo.get_invitations_by_team.side_effect = adapter_errors.TeamNotFoundError

        with pytest.raises(service_errors.TeamNotFoundError):
            await service.get_invitations_by_team(uuid.uuid4())


@pytest.mark.unit
class TestCancelInvitation:
    @pytest.mark.asyncio
    async def test_deletes_and_sends_kafka(self, service, repo, kafka):
        invitation = make_invitation()
        repo.get_invitation.return_value = invitation

        await service.cancel_invitation(invitation.id)

        repo.delete_invitation.assert_awaited_once_with(invitation.id)
        kafka.send_invitation_canceled.assert_awaited_once_with(invitation)

    @pytest.mark.asyncio
    async def test_raises_when_not_found(self, service, repo, kafka):
        repo.get_invitation.side_effect = adapter_errors.InvitationNotFoundError

        with pytest.raises(service_errors.InvitationNotFoundError):
            await service.cancel_invitation(uuid.uuid4())

        kafka.send_invitation_canceled.assert_not_called()


@pytest.mark.unit
class TestAcceptInvitation:
    @pytest.mark.asyncio
    async def test_accepts_and_sends_kafka(self, service, repo, kafka):
        invitation = make_invitation()
        repo.accept_invitation.return_value = invitation

        await service.accept_invitation(invitation.id)

        repo.accept_invitation.assert_awaited_once_with(invitation.id)
        kafka.send_invitation_accepted.assert_awaited_once_with(invitation)

    @pytest.mark.asyncio
    async def test_raises_not_found(self, service, repo, kafka):
        repo.accept_invitation.side_effect = adapter_errors.InvitationNotFoundError

        with pytest.raises(service_errors.InvitationNotFoundError):
            await service.accept_invitation(uuid.uuid4())

        kafka.send_invitation_accepted.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_already_in_team(self, service, repo, kafka):
        repo.accept_invitation.side_effect = (
            adapter_errors.ParticipantAlreadyInTeamError
        )

        with pytest.raises(service_errors.ParticipantAlreadyInTeam):
            await service.accept_invitation(uuid.uuid4())

        kafka.send_invitation_accepted.assert_not_called()


@pytest.mark.unit
class TestRejectInvitation:
    @pytest.mark.asyncio
    async def test_rejects_and_sends_kafka(self, service, repo, kafka):
        invitation = make_invitation()
        repo.get_invitation.return_value = invitation

        await service.reject_invitation(invitation.id)

        repo.delete_invitation.assert_awaited_once_with(invitation.id)
        kafka.send_invitation_rejected.assert_awaited_once_with(invitation)

    @pytest.mark.asyncio
    async def test_raises_not_found(self, service, repo, kafka):
        repo.get_invitation.side_effect = adapter_errors.InvitationNotFoundError

        with pytest.raises(service_errors.InvitationNotFoundError):
            await service.reject_invitation(uuid.uuid4())

        kafka.send_invitation_rejected.assert_not_called()


@pytest.mark.unit
class TestCreateJoinRequest:
    @pytest.mark.asyncio
    async def test_returns_id_and_sends_kafka(self, service, repo, kafka):
        join_request = make_join_request()

        result = await service.create_join_request(join_request)

        assert result == join_request.id
        repo.create_join_request.assert_awaited_once_with(join_request)
        kafka.send_join_request_created.assert_awaited_once_with(join_request)

    @pytest.mark.asyncio
    async def test_raises_already_in_team(self, service, repo, kafka):
        join_request = make_join_request(member=make_participant(have_team=True))

        with pytest.raises(service_errors.ParticipantAlreadyInTeam):
            await service.create_join_request(join_request)

        repo.create_join_request.assert_not_called()
        kafka.send_join_request_created.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_team_not_found(self, service, repo):
        repo.create_join_request.side_effect = adapter_errors.TeamNotFoundError

        with pytest.raises(service_errors.TeamNotFoundError):
            await service.create_join_request(make_join_request())

    @pytest.mark.asyncio
    async def test_raises_already_exists(self, service, repo):
        repo.create_join_request.side_effect = (
            adapter_errors.JoinRequestAlreadyExistsError
        )

        with pytest.raises(service_errors.JoinRequestAlreadyExistsError):
            await service.create_join_request(make_join_request())


@pytest.mark.unit
class TestGetJoinRequest:
    @pytest.mark.asyncio
    async def test_returns_join_request(self, service, repo):
        jr = make_join_request()
        repo.get_join_request.return_value = jr

        result = await service.get_join_request(jr.id)

        assert result == jr

    @pytest.mark.asyncio
    async def test_raises_not_found(self, service, repo):
        repo.get_join_request.side_effect = adapter_errors.JoinRequestNotFoundError

        with pytest.raises(service_errors.JoinRequestNotFoundError):
            await service.get_join_request(uuid.uuid4())


@pytest.mark.unit
class TestGetJoinRequestsForMember:
    @pytest.mark.asyncio
    async def test_returns_list(self, service, repo):
        items = [make_join_request(), make_join_request()]
        repo.get_join_requests_by_track_and_member.return_value = items

        result = await service.get_join_requests_for_member(uuid.uuid4(), uuid.uuid4())

        assert result == items


@pytest.mark.unit
class TestCancelJoinRequest:
    @pytest.mark.asyncio
    async def test_deletes_and_sends_kafka(self, service, repo, kafka):
        jr = make_join_request()
        repo.get_join_request.return_value = jr

        await service.cancel_join_request(jr.id)

        repo.delete_join_request.assert_awaited_once_with(jr.id)
        kafka.send_join_request_canceled.assert_awaited_once_with(jr)

    @pytest.mark.asyncio
    async def test_raises_not_found(self, service, repo, kafka):
        repo.get_join_request.side_effect = adapter_errors.JoinRequestNotFoundError

        with pytest.raises(service_errors.JoinRequestNotFoundError):
            await service.cancel_join_request(uuid.uuid4())

        kafka.send_join_request_canceled.assert_not_called()


@pytest.mark.unit
class TestAcceptJoinRequest:
    @pytest.mark.asyncio
    async def test_accepts_and_sends_kafka(self, service, repo, kafka):
        jr = make_join_request()
        repo.accept_join_request.return_value = jr

        await service.accept_join_request(jr.id)

        repo.accept_join_request.assert_awaited_once_with(jr.id)
        kafka.send_join_request_accepted.assert_awaited_once_with(jr)

    @pytest.mark.asyncio
    async def test_raises_not_found(self, service, repo, kafka):
        repo.accept_join_request.side_effect = adapter_errors.JoinRequestNotFoundError

        with pytest.raises(service_errors.JoinRequestNotFoundError):
            await service.accept_join_request(uuid.uuid4())

        kafka.send_join_request_accepted.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_already_in_team(self, service, repo, kafka):
        repo.accept_join_request.side_effect = (
            adapter_errors.ParticipantAlreadyInTeamError
        )

        with pytest.raises(service_errors.ParticipantAlreadyInTeam):
            await service.accept_join_request(uuid.uuid4())

        kafka.send_join_request_accepted.assert_not_called()


@pytest.mark.unit
class TestRejectJoinRequest:
    @pytest.mark.asyncio
    async def test_rejects_and_sends_kafka(self, service, repo, kafka):
        jr = make_join_request()
        repo.get_join_request.return_value = jr

        await service.reject_join_request(jr.id)

        repo.delete_join_request.assert_awaited_once_with(jr.id)
        kafka.send_join_request_rejected.assert_awaited_once_with(jr)

    @pytest.mark.asyncio
    async def test_raises_not_found(self, service, repo, kafka):
        repo.get_join_request.side_effect = adapter_errors.JoinRequestNotFoundError

        with pytest.raises(service_errors.JoinRequestNotFoundError):
            await service.reject_join_request(uuid.uuid4())

        kafka.send_join_request_rejected.assert_not_called()
