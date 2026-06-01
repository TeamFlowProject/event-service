import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.controller.http.invitation.router import create_invitation_router
from src.models.event import Participant
from src.models.invitation import Invitation, JoinRequest
from src.models.track import Role
from src.service.errors import (
    InvitationAlreadyExistsError,
    InvitationNotFoundError,
    JoinRequestAlreadyExistsError,
    JoinRequestNotFoundError,
    ParticipantAlreadyInTeam,
    ParticipantNotFoundError,
    RoleNotFoundError,
    TeamNotFoundError,
)


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
        description="hello",
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
        description="please",
    )
    defaults.update(kwargs)
    return JoinRequest(**defaults)  # type: ignore


def invitation_payload(**kwargs) -> dict:
    defaults = dict(
        team_id=str(uuid.uuid4()),
        owner_id=str(uuid.uuid4()),
        member_id=str(uuid.uuid4()),
        role_id=str(uuid.uuid4()),
        description="please join",
    )
    defaults.update(kwargs)
    return defaults


def join_request_payload(**kwargs) -> dict:
    defaults = dict(
        team_id=str(uuid.uuid4()),
        owner_id=str(uuid.uuid4()),
        member_id=str(uuid.uuid4()),
        role_id=str(uuid.uuid4()),
        description="I want to join",
    )
    defaults.update(kwargs)
    return defaults


@pytest.fixture
def service():
    return AsyncMock()


@pytest.fixture
def client(service):
    app = FastAPI()
    app.include_router(create_invitation_router(service))
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-User-Id": str(uuid.uuid4())},
    )


@pytest.mark.unit
class TestCreateInvitation:
    @pytest.mark.asyncio
    async def test_returns_201(self, client, service):
        invitation_id = uuid.uuid4()
        service.create_invitation.return_value = invitation_id

        async with client as c:
            resp = await c.post("/api/v1/invitations", json=invitation_payload())

        assert resp.status_code == 201
        assert resp.json() == {"id": str(invitation_id)}
        service.create_invitation.assert_called_once()

    @pytest.mark.asyncio
    async def test_404_when_team_not_found(self, client, service):
        service.create_invitation.side_effect = TeamNotFoundError

        async with client as c:
            resp = await c.post("/api/v1/invitations", json=invitation_payload())

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_404_when_participant_not_found(self, client, service):
        service.create_invitation.side_effect = ParticipantNotFoundError

        async with client as c:
            resp = await c.post("/api/v1/invitations", json=invitation_payload())

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_404_when_role_not_found(self, client, service):
        service.create_invitation.side_effect = RoleNotFoundError

        async with client as c:
            resp = await c.post("/api/v1/invitations", json=invitation_payload())

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_409_when_already_exists(self, client, service):
        service.create_invitation.side_effect = InvitationAlreadyExistsError

        async with client as c:
            resp = await c.post("/api/v1/invitations", json=invitation_payload())

        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_409_when_already_in_team(self, client, service):
        service.create_invitation.side_effect = ParticipantAlreadyInTeam

        async with client as c:
            resp = await c.post("/api/v1/invitations", json=invitation_payload())

        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_422_when_payload_invalid(self, client):
        async with client as c:
            resp = await c.post("/api/v1/invitations", json={"bad": "payload"})

        assert resp.status_code == 422


@pytest.mark.unit
class TestGetInvitation:
    @pytest.mark.asyncio
    async def test_returns_invitation(self, client, service):
        invitation = make_invitation()
        service.get_invitation.return_value = invitation

        async with client as c:
            resp = await c.get(f"/api/v1/invitations/{invitation.id}")

        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(invitation.id)
        assert body["team_id"] == str(invitation.team_id)
        assert body["owner"]["id"] == str(invitation.owner.id)
        assert body["member"]["id"] == str(invitation.member.id)
        assert body["role"]["id"] == str(invitation.role.id)
        assert body["description"] == invitation.description

    @pytest.mark.asyncio
    async def test_404_when_not_found(self, client, service):
        service.get_invitation.side_effect = InvitationNotFoundError

        async with client as c:
            resp = await c.get(f"/api/v1/invitations/{uuid.uuid4()}")

        assert resp.status_code == 404


@pytest.mark.unit
class TestGetInvitationsByTeam:
    @pytest.mark.asyncio
    async def test_returns_list(self, client, service):
        invitations = [make_invitation(), make_invitation()]
        service.get_invitations_by_team.return_value = invitations

        async with client as c:
            resp = await c.get(f"/api/v1/teams/{uuid.uuid4()}/invitations")

        assert resp.status_code == 200
        assert len(resp.json()["invitations"]) == 2

    @pytest.mark.asyncio
    async def test_empty(self, client, service):
        service.get_invitations_by_team.return_value = []

        async with client as c:
            resp = await c.get(f"/api/v1/teams/{uuid.uuid4()}/invitations")

        assert resp.status_code == 200
        assert resp.json() == {"invitations": []}

    @pytest.mark.asyncio
    async def test_404_when_team_not_found(self, client, service):
        service.get_invitations_by_team.side_effect = TeamNotFoundError

        async with client as c:
            resp = await c.get(f"/api/v1/teams/{uuid.uuid4()}/invitations")

        assert resp.status_code == 404


@pytest.mark.unit
class TestDeleteInvitation:
    @pytest.mark.asyncio
    async def test_204(self, client, service):
        async with client as c:
            resp = await c.delete(f"/api/v1/invitations/{uuid.uuid4()}")

        assert resp.status_code == 204
        service.cancel_invitation.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_404(self, client, service):
        service.cancel_invitation.side_effect = InvitationNotFoundError

        async with client as c:
            resp = await c.delete(f"/api/v1/invitations/{uuid.uuid4()}")

        assert resp.status_code == 404


@pytest.mark.unit
class TestDecideInvitation:
    @pytest.mark.asyncio
    async def test_accept_204(self, client, service):
        async with client as c:
            resp = await c.put(
                f"/api/v1/invitations/{uuid.uuid4()}", json={"decision": "ACCEPT"}
            )

        assert resp.status_code == 204
        service.accept_invitation.assert_awaited_once()
        service.reject_invitation.assert_not_called()

    @pytest.mark.asyncio
    async def test_reject_204(self, client, service):
        async with client as c:
            resp = await c.put(
                f"/api/v1/invitations/{uuid.uuid4()}", json={"decision": "REJECT"}
            )

        assert resp.status_code == 204
        service.reject_invitation.assert_awaited_once()
        service.accept_invitation.assert_not_called()

    @pytest.mark.asyncio
    async def test_404_when_not_found(self, client, service):
        service.accept_invitation.side_effect = InvitationNotFoundError

        async with client as c:
            resp = await c.put(
                f"/api/v1/invitations/{uuid.uuid4()}", json={"decision": "ACCEPT"}
            )

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_409_when_already_in_team(self, client, service):
        service.accept_invitation.side_effect = ParticipantAlreadyInTeam

        async with client as c:
            resp = await c.put(
                f"/api/v1/invitations/{uuid.uuid4()}", json={"decision": "ACCEPT"}
            )

        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_422_when_bad_decision(self, client):
        async with client as c:
            resp = await c.put(
                f"/api/v1/invitations/{uuid.uuid4()}", json={"decision": "MAYBE"}
            )

        assert resp.status_code == 422


@pytest.mark.unit
class TestCreateJoinRequest:
    @pytest.mark.asyncio
    async def test_201(self, client, service):
        jr_id = uuid.uuid4()
        service.create_join_request.return_value = jr_id

        async with client as c:
            resp = await c.post("/api/v1/join_requests", json=join_request_payload())

        assert resp.status_code == 201
        assert resp.json() == {"id": str(jr_id)}

    @pytest.mark.asyncio
    async def test_404_team_not_found(self, client, service):
        service.create_join_request.side_effect = TeamNotFoundError

        async with client as c:
            resp = await c.post("/api/v1/join_requests", json=join_request_payload())

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_409_already_exists(self, client, service):
        service.create_join_request.side_effect = JoinRequestAlreadyExistsError

        async with client as c:
            resp = await c.post("/api/v1/join_requests", json=join_request_payload())

        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_409_already_in_team(self, client, service):
        service.create_join_request.side_effect = ParticipantAlreadyInTeam

        async with client as c:
            resp = await c.post("/api/v1/join_requests", json=join_request_payload())

        assert resp.status_code == 409


@pytest.mark.unit
class TestGetMyJoinRequests:
    @pytest.mark.asyncio
    async def test_returns_list(self, client, service):
        user_id = uuid.uuid4()
        track_id = uuid.uuid4()
        items = [make_join_request(), make_join_request()]
        service.get_join_requests_for_member.return_value = items

        async with client as c:
            resp = await c.get(
                f"/api/v1/track/{track_id}/join_requests",
                headers={"X-User-Id": str(user_id)},
            )

        assert resp.status_code == 200
        assert len(resp.json()["join_requests"]) == 2
        service.get_join_requests_for_member.assert_awaited_once_with(track_id, user_id)

    @pytest.mark.asyncio
    async def test_missing_header_returns_401(self, client):
        async with client as c:
            c.headers.pop("X-User-Id", None)
            resp = await c.get(f"/api/v1/track/{uuid.uuid4()}/join_requests")

        assert resp.status_code == 401


@pytest.mark.unit
class TestGetJoinRequest:
    @pytest.mark.asyncio
    async def test_returns(self, client, service):
        jr = make_join_request()
        service.get_join_request.return_value = jr

        async with client as c:
            resp = await c.get(f"/api/v1/track/{uuid.uuid4()}/join_requests/{jr.id}")

        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(jr.id)
        assert body["team_id"] == str(jr.team_id)

    @pytest.mark.asyncio
    async def test_404(self, client, service):
        service.get_join_request.side_effect = JoinRequestNotFoundError

        async with client as c:
            resp = await c.get(
                f"/api/v1/track/{uuid.uuid4()}/join_requests/{uuid.uuid4()}"
            )

        assert resp.status_code == 404


@pytest.mark.unit
class TestCancelJoinRequest:
    @pytest.mark.asyncio
    async def test_204_when_owner(self, client, service):
        user_id = uuid.uuid4()
        jr = make_join_request(member=make_participant(id=user_id))
        service.get_join_request.return_value = jr

        async with client as c:
            resp = await c.delete(
                f"/api/v1/join_requests/{jr.id}",
                headers={"X-User-Id": str(user_id)},
            )

        assert resp.status_code == 204
        service.cancel_join_request.assert_awaited_once_with(jr.id)

    @pytest.mark.asyncio
    async def test_403_when_not_owner(self, client, service):
        jr = make_join_request()
        service.get_join_request.return_value = jr

        async with client as c:
            resp = await c.delete(
                f"/api/v1/join_requests/{jr.id}",
                headers={"X-User-Id": str(uuid.uuid4())},
            )

        assert resp.status_code == 403
        service.cancel_join_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_404(self, client, service):
        service.get_join_request.side_effect = JoinRequestNotFoundError

        async with client as c:
            resp = await c.delete(
                f"/api/v1/join_requests/{uuid.uuid4()}",
                headers={"X-User-Id": str(uuid.uuid4())},
            )

        assert resp.status_code == 404


@pytest.mark.unit
class TestDecideJoinRequest:
    @pytest.mark.asyncio
    async def test_accept_204(self, client, service):
        async with client as c:
            resp = await c.put(
                f"/api/v1/join_requests/{uuid.uuid4()}",
                json={"decision": "ACCEPT"},
            )

        assert resp.status_code == 204
        service.accept_join_request.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_reject_204(self, client, service):
        async with client as c:
            resp = await c.put(
                f"/api/v1/join_requests/{uuid.uuid4()}",
                json={"decision": "REJECT"},
            )

        assert resp.status_code == 204
        service.reject_join_request.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_404(self, client, service):
        service.accept_join_request.side_effect = JoinRequestNotFoundError

        async with client as c:
            resp = await c.put(
                f"/api/v1/join_requests/{uuid.uuid4()}",
                json={"decision": "ACCEPT"},
            )

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_409_already_in_team(self, client, service):
        service.accept_join_request.side_effect = ParticipantAlreadyInTeam

        async with client as c:
            resp = await c.put(
                f"/api/v1/join_requests/{uuid.uuid4()}",
                json={"decision": "ACCEPT"},
            )

        assert resp.status_code == 409
