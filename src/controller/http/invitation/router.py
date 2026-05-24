import uuid
from typing import cast

from fastapi import APIRouter, Header, HTTPException
from uuid_extensions import uuid7

from src.controller.http.invitation.protocols import InvitationService
from src.controller.http.invitation.schemas import (
    CreateInvitationRequest,
    CreateJoinRequestRequest,
    DecisionEnum,
    DecisionRequest,
    GetInvitationResponse,
    GetInvitationsResponse,
    GetJoinRequestResponse,
    GetJoinRequestsResponse,
    Participant,
    Role,
)
from src.models.event import Participant as ParticipantModel
from src.models.invitation import Invitation, JoinRequest
from src.models.track import Role as RoleModel
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


def create_invitation_router(service: InvitationService) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["invitation"])

    @router.post("/invitations", response_model=dict, status_code=201)
    async def create_invitation(request: CreateInvitationRequest):
        invitation_id = cast(uuid.UUID, uuid7())
        invitation = _invitation_from_request(request, invitation_id)
        try:
            created_id = await service.create_invitation(invitation)
        except TeamNotFoundError:
            raise HTTPException(status_code=404, detail="Team not found")
        except ParticipantNotFoundError:
            raise HTTPException(status_code=404, detail="Participant not found")
        except RoleNotFoundError:
            raise HTTPException(status_code=404, detail="Role not found")
        except InvitationAlreadyExistsError:
            raise HTTPException(status_code=409, detail="Invitation already exists")
        except ParticipantAlreadyInTeam:
            raise HTTPException(status_code=409, detail="Participant already in a team")
        return {"id": str(created_id)}

    @router.get("/invitations/{invitation_id}", response_model=GetInvitationResponse)
    async def get_invitation(invitation_id: uuid.UUID):
        try:
            invitation = await service.get_invitation(invitation_id)
        except InvitationNotFoundError:
            raise HTTPException(status_code=404, detail="Invitation not found")
        return _invitation_to_response(invitation)

    @router.get("/teams/{team_id}/invitations", response_model=GetInvitationsResponse)
    async def get_invitations_by_team(team_id: uuid.UUID):
        try:
            invitations = await service.get_invitations_by_team(team_id)
        except TeamNotFoundError:
            raise HTTPException(status_code=404, detail="Team not found")
        return GetInvitationsResponse(
            invitations=[_invitation_to_response(i) for i in invitations]
        )

    @router.delete("/invitations/{invitation_id}", status_code=204)
    async def delete_invitation(invitation_id: uuid.UUID):
        try:
            await service.cancel_invitation(invitation_id)
        except InvitationNotFoundError:
            raise HTTPException(status_code=404, detail="Invitation not found")

    @router.put("/invitations/{invitation_id}", status_code=204)
    async def decide_invitation(invitation_id: uuid.UUID, request: DecisionRequest):
        try:
            if request.decision == DecisionEnum.ACCEPT:
                await service.accept_invitation(invitation_id)
            else:
                await service.reject_invitation(invitation_id)
        except InvitationNotFoundError:
            raise HTTPException(status_code=404, detail="Invitation not found")
        except ParticipantAlreadyInTeam:
            raise HTTPException(status_code=409, detail="Participant already in a team")

    @router.post("/join_requests", response_model=dict, status_code=201)
    async def create_join_request(request: CreateJoinRequestRequest):
        join_request_id = cast(uuid.UUID, uuid7())
        join_request = _join_request_from_request(request, join_request_id)
        try:
            created_id = await service.create_join_request(join_request)
        except TeamNotFoundError:
            raise HTTPException(status_code=404, detail="Team not found")
        except ParticipantNotFoundError:
            raise HTTPException(status_code=404, detail="Participant not found")
        except RoleNotFoundError:
            raise HTTPException(status_code=404, detail="Role not found")
        except JoinRequestAlreadyExistsError:
            raise HTTPException(status_code=409, detail="JoinRequest already exists")
        except ParticipantAlreadyInTeam:
            raise HTTPException(status_code=409, detail="Participant already in a team")
        return {"id": str(created_id)}

    @router.get(
        "/track/{track_id}/join_requests",
        response_model=GetJoinRequestsResponse,
    )
    async def get_my_join_requests(
        track_id: uuid.UUID, x_user_id: uuid.UUID = Header(..., alias="X-User-Id")
    ):
        join_requests = await service.get_join_requests_for_member(track_id, x_user_id)
        return GetJoinRequestsResponse(
            join_requests=[_join_request_to_response(jr) for jr in join_requests]
        )

    @router.get(
        "/track/{track_id}/join_requests/{join_request_id}",
        response_model=GetJoinRequestResponse,
    )
    async def get_join_request(track_id: uuid.UUID, join_request_id: uuid.UUID):
        try:
            join_request = await service.get_join_request(join_request_id)
        except JoinRequestNotFoundError:
            raise HTTPException(status_code=404, detail="JoinRequest not found")
        return _join_request_to_response(join_request)

    @router.delete("/join_requests/{join_request_id}", status_code=204)
    async def cancel_join_request(
        join_request_id: uuid.UUID,
        x_user_id: uuid.UUID = Header(..., alias="X-User-Id"),
    ):
        try:
            join_request = await service.get_join_request(join_request_id)
        except JoinRequestNotFoundError:
            raise HTTPException(status_code=404, detail="JoinRequest not found")

        if join_request.member.id != x_user_id:
            raise HTTPException(
                status_code=403,
                detail="You can only cancel your own join requests",
            )

        try:
            await service.cancel_join_request(join_request_id)
        except JoinRequestNotFoundError:
            raise HTTPException(status_code=404, detail="JoinRequest not found")

    @router.put("/join_requests/{join_request_id}", status_code=204)
    async def decide_join_request(join_request_id: uuid.UUID, request: DecisionRequest):
        try:
            if request.decision == DecisionEnum.ACCEPT:
                await service.accept_join_request(join_request_id)
            else:
                await service.reject_join_request(join_request_id)
        except JoinRequestNotFoundError:
            raise HTTPException(status_code=404, detail="JoinRequest not found")
        except ParticipantAlreadyInTeam:
            raise HTTPException(status_code=409, detail="Participant already in a team")

    return router


def _invitation_from_request(
    request: CreateInvitationRequest, invitation_id: uuid.UUID
) -> Invitation:
    owner_stub = ParticipantModel(
        id=request.owner_id,
        event_id=uuid.UUID(int=0),
        name="",
        surname="",
        patronymic="",
        have_team=False,
    )
    member_stub = ParticipantModel(
        id=request.member_id,
        event_id=uuid.UUID(int=0),
        name="",
        surname="",
        patronymic="",
        have_team=False,
    )
    role_stub = RoleModel(
        id=request.role_id,
        track_id=uuid.UUID(int=0),
        name="",
        description="",
        count=0,
    )
    return Invitation(
        id=invitation_id,
        team_id=request.team_id,
        owner=owner_stub,
        member=member_stub,
        role=role_stub,
        description=request.description,
    )


def _join_request_from_request(
    request: CreateJoinRequestRequest, join_request_id: uuid.UUID
) -> JoinRequest:
    owner_stub = ParticipantModel(
        id=request.owner_id,
        event_id=uuid.UUID(int=0),
        name="",
        surname="",
        patronymic="",
        have_team=False,
    )
    member_stub = ParticipantModel(
        id=request.member_id,
        event_id=uuid.UUID(int=0),
        name="",
        surname="",
        patronymic="",
        have_team=False,
    )
    role_stub = RoleModel(
        id=request.role_id,
        track_id=uuid.UUID(int=0),
        name="",
        description="",
        count=0,
    )
    return JoinRequest(
        id=join_request_id,
        team_id=request.team_id,
        owner=owner_stub,
        member=member_stub,
        role=role_stub,
        description=request.description,
    )


def _participant_to_response(p: ParticipantModel) -> Participant:
    return Participant(
        id=p.id,
        event_id=p.event_id,
        name=p.name,
        surname=p.surname,
        patronymic=p.patronymic,
        have_team=p.have_team,
        role_id=p.role_id,
    )


def _role_to_response(r: RoleModel) -> Role:
    return Role(
        id=r.id,
        track_id=r.track_id,
        name=r.name,
        description=r.description,
        count=r.count,
    )


def _invitation_to_response(invitation: Invitation) -> GetInvitationResponse:
    return GetInvitationResponse(
        id=invitation.id,
        team_id=invitation.team_id,
        owner=_participant_to_response(invitation.owner),
        member=_participant_to_response(invitation.member),
        role=_role_to_response(invitation.role),
        description=invitation.description,
    )


def _join_request_to_response(jr: JoinRequest) -> GetJoinRequestResponse:
    return GetJoinRequestResponse(
        id=jr.id,
        team_id=jr.team_id,
        owner=_participant_to_response(jr.owner),
        member=_participant_to_response(jr.member),
        role=_role_to_response(jr.role),
        description=jr.description,
    )
