import uuid
from typing import Optional, cast

from fastapi import APIRouter, Header, HTTPException
from uuid_extensions import uuid7
from loguru import logger
from opentelemetry import trace

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

tracer = trace.get_tracer(__name__)


def create_invitation_router(service: InvitationService) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["invitation"])

    @router.post("/invitations", response_model=dict, status_code=201)
    async def create_invitation(
        request: CreateInvitationRequest,
        x_user_id: Optional[uuid.UUID] = Header(None, alias="X-User-Id"),
    ):
        if x_user_id is None:
            raise HTTPException(status_code=401, detail="X-User-Id header missing")
        invitation_id = cast(uuid.UUID, uuid7())
        span = trace.get_current_span()
        span.set_attribute("invitation.id", str(invitation_id))
        span.set_attribute("team.id", str(request.team_id))

        logger.info(
            "invitation_creation_started",
            invitation_id=str(invitation_id),
            team_id=str(request.team_id),
            member_id=str(request.member_id),
        )

        invitation = _invitation_from_request(request, invitation_id)
        try:
            created_id = await service.create_invitation(invitation)
            logger.info("invitation_created", invitation_id=str(created_id))
            return {"id": str(created_id)}
        except TeamNotFoundError:
            logger.warning("team_not_found", team_id=str(request.team_id))
            raise HTTPException(status_code=404, detail="Team not found")
        except ParticipantNotFoundError:
            logger.warning("participant_not_found", invitation_id=str(invitation_id))
            raise HTTPException(status_code=404, detail="Participant not found")
        except RoleNotFoundError:
            logger.warning("role_not_found", invitation_id=str(invitation_id))
            raise HTTPException(status_code=404, detail="Role not found")
        except InvitationAlreadyExistsError:
            logger.warning(
                "invitation_already_exists", invitation_id=str(invitation_id)
            )
            raise HTTPException(status_code=409, detail="Invitation already exists")
        except ParticipantAlreadyInTeam:
            logger.warning(
                "participant_already_in_team", invitation_id=str(invitation_id)
            )
            raise HTTPException(status_code=409, detail="Participant already in a team")
        except Exception as e:
            logger.error(
                "invitation_creation_failed",
                invitation_id=str(invitation_id),
                error=str(e),
            )
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            raise HTTPException(status_code=500, detail="Failed to create invitation")

    @router.get("/invitations/{invitation_id}", response_model=GetInvitationResponse)
    async def get_invitation(
        invitation_id: uuid.UUID,
        x_user_id: Optional[uuid.UUID] = Header(None, alias="X-User-Id"),
    ):
        if x_user_id is None:
            raise HTTPException(status_code=401, detail="X-User-Id header missing")
        span = trace.get_current_span()
        span.set_attribute("invitation.id", str(invitation_id))

        logger.info("invitation_fetch_started", invitation_id=str(invitation_id))

        try:
            invitation = await service.get_invitation(invitation_id)
            logger.info("invitation_fetched", invitation_id=str(invitation_id))
            return _invitation_to_response(invitation)
        except InvitationNotFoundError:
            logger.warning("invitation_not_found", invitation_id=str(invitation_id))
            raise HTTPException(status_code=404, detail="Invitation not found")
        except Exception as e:
            logger.error(
                "invitation_fetch_failed",
                invitation_id=str(invitation_id),
                error=str(e),
            )
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            raise HTTPException(status_code=500, detail="Failed to fetch invitation")

    @router.get("/teams/{team_id}/invitations", response_model=GetInvitationsResponse)
    async def get_invitations_by_team(
        team_id: uuid.UUID,
        x_user_id: Optional[uuid.UUID] = Header(None, alias="X-User-Id"),
    ):
        if x_user_id is None:
            raise HTTPException(status_code=401, detail="X-User-Id header missing")
        span = trace.get_current_span()
        span.set_attribute("team.id", str(team_id))

        logger.info("team_invitations_fetch_started", team_id=str(team_id))

        try:
            invitations = await service.get_invitations_by_team(team_id)
            logger.info(
                "team_invitations_fetched", team_id=str(team_id), count=len(invitations)
            )
            return GetInvitationsResponse(
                invitations=[_invitation_to_response(i) for i in invitations]
            )
        except TeamNotFoundError:
            logger.warning("team_not_found", team_id=str(team_id))
            raise HTTPException(status_code=404, detail="Team not found")
        except Exception as e:
            logger.error(
                "team_invitations_fetch_failed", team_id=str(team_id), error=str(e)
            )
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            raise HTTPException(
                status_code=500, detail="Failed to fetch team invitations"
            )

    @router.get("/users/{user_id}/invitations", response_model=GetInvitationsResponse)
    async def get_invitations_by_member(
        user_id: uuid.UUID,
        x_user_id: Optional[uuid.UUID] = Header(None, alias="X-User-Id"),
    ):
        if x_user_id is None:
            raise HTTPException(status_code=401, detail="X-User-Id header missing")
        span = trace.get_current_span()
        span.set_attribute("member.id", str(user_id))

        logger.info("member_invitations_fetch_started", member_id=str(user_id))

        try:
            invitations = await service.get_invitations_by_member(user_id)
            logger.info(
                "member_invitations_fetched",
                member_id=str(user_id),
                count=len(invitations),
            )
            return GetInvitationsResponse(
                invitations=[_invitation_to_response(i) for i in invitations]
            )
        except Exception as e:
            logger.error(
                "member_invitations_fetch_failed",
                member_id=str(user_id),
                error=str(e),
            )
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            raise HTTPException(
                status_code=500, detail="Failed to fetch member invitations"
            )

    @router.delete("/invitations/{invitation_id}", status_code=204)
    async def delete_invitation(
        invitation_id: uuid.UUID,
        x_user_id: Optional[uuid.UUID] = Header(None, alias="X-User-Id"),
    ):
        if x_user_id is None:
            raise HTTPException(status_code=401, detail="X-User-Id header missing")
        span = trace.get_current_span()
        span.set_attribute("invitation.id", str(invitation_id))

        logger.info("invitation_deletion_started", invitation_id=str(invitation_id))

        try:
            await service.cancel_invitation(invitation_id)
            logger.info("invitation_deleted", invitation_id=str(invitation_id))
        except InvitationNotFoundError:
            logger.warning("invitation_not_found", invitation_id=str(invitation_id))
            raise HTTPException(status_code=404, detail="Invitation not found")
        except Exception as e:
            logger.error(
                "invitation_deletion_failed",
                invitation_id=str(invitation_id),
                error=str(e),
            )
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            raise HTTPException(status_code=500, detail="Failed to delete invitation")

    @router.put("/invitations/{invitation_id}", status_code=204)
    async def decide_invitation(
        invitation_id: uuid.UUID,
        request: DecisionRequest,
        x_user_id: Optional[uuid.UUID] = Header(None, alias="X-User-Id"),
    ):
        if x_user_id is None:
            raise HTTPException(status_code=401, detail="X-User-Id header missing")
        span = trace.get_current_span()
        span.set_attribute("invitation.id", str(invitation_id))
        span.set_attribute("decision", request.decision.value)

        logger.info(
            "invitation_decision_started",
            invitation_id=str(invitation_id),
            decision=request.decision.value,
        )

        try:
            if request.decision == DecisionEnum.ACCEPT:
                await service.accept_invitation(invitation_id)
            else:
                await service.reject_invitation(invitation_id)
            logger.info(
                "invitation_decision_completed",
                invitation_id=str(invitation_id),
                decision=request.decision.value,
            )
        except InvitationNotFoundError:
            logger.warning("invitation_not_found", invitation_id=str(invitation_id))
            raise HTTPException(status_code=404, detail="Invitation not found")
        except ParticipantAlreadyInTeam:
            logger.warning(
                "participant_already_in_team", invitation_id=str(invitation_id)
            )
            raise HTTPException(status_code=409, detail="Participant already in a team")
        except Exception as e:
            logger.error(
                "invitation_decision_failed",
                invitation_id=str(invitation_id),
                error=str(e),
            )
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            raise HTTPException(status_code=500, detail="Failed to decide invitation")

    @router.post("/join_requests", response_model=dict, status_code=201)
    async def create_join_request(
        request: CreateJoinRequestRequest,
        x_user_id: Optional[uuid.UUID] = Header(None, alias="X-User-Id"),
    ):
        if x_user_id is None:
            raise HTTPException(status_code=401, detail="X-User-Id header missing")
        join_request_id = cast(uuid.UUID, uuid7())
        span = trace.get_current_span()
        span.set_attribute("join_request.id", str(join_request_id))
        span.set_attribute("team.id", str(request.team_id))

        logger.info(
            "join_request_creation_started",
            join_request_id=str(join_request_id),
            team_id=str(request.team_id),
            member_id=str(request.member_id),
        )

        join_request = _join_request_from_request(request, join_request_id)
        try:
            created_id = await service.create_join_request(join_request)
            logger.info("join_request_created", join_request_id=str(created_id))
            return {"id": str(created_id)}
        except TeamNotFoundError:
            logger.warning("team_not_found", team_id=str(request.team_id))
            raise HTTPException(status_code=404, detail="Team not found")
        except ParticipantNotFoundError:
            logger.warning(
                "participant_not_found", join_request_id=str(join_request_id)
            )
            raise HTTPException(status_code=404, detail="Participant not found")
        except RoleNotFoundError:
            logger.warning("role_not_found", join_request_id=str(join_request_id))
            raise HTTPException(status_code=404, detail="Role not found")
        except JoinRequestAlreadyExistsError:
            logger.warning(
                "join_request_already_exists", join_request_id=str(join_request_id)
            )
            raise HTTPException(status_code=409, detail="JoinRequest already exists")
        except ParticipantAlreadyInTeam:
            logger.warning(
                "participant_already_in_team", join_request_id=str(join_request_id)
            )
            raise HTTPException(status_code=409, detail="Participant already in a team")
        except Exception as e:
            logger.error(
                "join_request_creation_failed",
                join_request_id=str(join_request_id),
                error=str(e),
            )
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            raise HTTPException(status_code=500, detail="Failed to create join request")

    @router.get(
        "/track/{track_id}/join_requests",
        response_model=GetJoinRequestsResponse,
    )
    async def get_my_join_requests(
        track_id: uuid.UUID,
        x_user_id: Optional[uuid.UUID] = Header(None, alias="X-User-Id"),
    ):
        if x_user_id is None:
            raise HTTPException(status_code=401, detail="X-User-Id header missing")
        span = trace.get_current_span()
        span.set_attribute("track.id", str(track_id))
        span.set_attribute("user.id", str(x_user_id))

        logger.info(
            "join_requests_fetch_started",
            track_id=str(track_id),
            user_id=str(x_user_id),
        )

        try:
            join_requests = await service.get_join_requests_for_member(
                track_id, x_user_id
            )
            logger.info(
                "join_requests_fetched",
                track_id=str(track_id),
                user_id=str(x_user_id),
                count=len(join_requests),
            )
            return GetJoinRequestsResponse(
                join_requests=[_join_request_to_response(jr) for jr in join_requests]
            )
        except Exception as e:
            logger.error(
                "join_requests_fetch_failed",
                track_id=str(track_id),
                user_id=str(x_user_id),
                error=str(e),
            )
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            raise HTTPException(status_code=500, detail="Failed to fetch join requests")

    @router.get(
        "/track/{track_id}/join_requests/{join_request_id}",
        response_model=GetJoinRequestResponse,
    )
    async def get_join_request(
        track_id: uuid.UUID,
        join_request_id: uuid.UUID,
        x_user_id: Optional[uuid.UUID] = Header(None, alias="X-User-Id"),
    ):
        if x_user_id is None:
            raise HTTPException(status_code=401, detail="X-User-Id header missing")
        span = trace.get_current_span()
        span.set_attribute("join_request.id", str(join_request_id))
        span.set_attribute("track.id", str(track_id))

        logger.info(
            "join_request_fetch_started",
            join_request_id=str(join_request_id),
            track_id=str(track_id),
        )

        try:
            join_request = await service.get_join_request(join_request_id)
            logger.info("join_request_fetched", join_request_id=str(join_request_id))
            return _join_request_to_response(join_request)
        except JoinRequestNotFoundError:
            logger.warning(
                "join_request_not_found", join_request_id=str(join_request_id)
            )
            raise HTTPException(status_code=404, detail="JoinRequest not found")
        except Exception as e:
            logger.error(
                "join_request_fetch_failed",
                join_request_id=str(join_request_id),
                error=str(e),
            )
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            raise HTTPException(status_code=500, detail="Failed to fetch join request")

    @router.get(
        "/teams/{team_id}/join_requests",
        response_model=GetJoinRequestsResponse,
    )
    async def get_join_requests_by_team(
        team_id: uuid.UUID,
        x_user_id: Optional[uuid.UUID] = Header(None, alias="X-User-Id"),
    ):
        if x_user_id is None:
            raise HTTPException(status_code=401, detail="X-User-Id header missing")
        span = trace.get_current_span()
        span.set_attribute("team.id", str(team_id))

        logger.info("team_join_requests_fetch_started", team_id=str(team_id))

        try:
            join_requests = await service.get_join_requests_by_team(team_id)
            logger.info(
                "team_join_requests_fetched",
                team_id=str(team_id),
                count=len(join_requests),
            )
            return GetJoinRequestsResponse(
                join_requests=[_join_request_to_response(jr) for jr in join_requests]
            )
        except TeamNotFoundError:
            logger.warning("team_not_found", team_id=str(team_id))
            raise HTTPException(status_code=404, detail="Team not found")
        except Exception as e:
            logger.error(
                "team_join_requests_fetch_failed",
                team_id=str(team_id),
                error=str(e),
            )
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            raise HTTPException(
                status_code=500, detail="Failed to fetch team join requests"
            )

    @router.get(
        "/users/{user_id}/owned_join_requests",
        response_model=GetJoinRequestsResponse,
    )
    async def get_join_requests_by_owner(
        user_id: uuid.UUID,
        x_user_id: Optional[uuid.UUID] = Header(None, alias="X-User-Id"),
    ):
        if x_user_id is None:
            raise HTTPException(status_code=401, detail="X-User-Id header missing")
        span = trace.get_current_span()
        span.set_attribute("owner.id", str(user_id))

        logger.info("owner_join_requests_fetch_started", owner_id=str(user_id))

        try:
            join_requests = await service.get_join_requests_by_owner(user_id)
            logger.info(
                "owner_join_requests_fetched",
                owner_id=str(user_id),
                count=len(join_requests),
            )
            return GetJoinRequestsResponse(
                join_requests=[_join_request_to_response(jr) for jr in join_requests]
            )
        except Exception as e:
            logger.error(
                "owner_join_requests_fetch_failed",
                owner_id=str(user_id),
                error=str(e),
            )
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            raise HTTPException(
                status_code=500, detail="Failed to fetch owner join requests"
            )

    @router.delete("/join_requests/{join_request_id}", status_code=204)
    async def cancel_join_request(
        join_request_id: uuid.UUID,
        x_user_id: Optional[uuid.UUID] = Header(None, alias="X-User-Id"),
    ):
        if x_user_id is None:
            raise HTTPException(status_code=401, detail="X-User-Id header missing")
        span = trace.get_current_span()
        span.set_attribute("join_request.id", str(join_request_id))
        span.set_attribute("user.id", str(x_user_id))

        logger.info(
            "join_request_cancellation_started",
            join_request_id=str(join_request_id),
            user_id=str(x_user_id),
        )

        try:
            join_request = await service.get_join_request(join_request_id)
        except JoinRequestNotFoundError:
            logger.warning(
                "join_request_not_found", join_request_id=str(join_request_id)
            )
            raise HTTPException(status_code=404, detail="JoinRequest not found")

        if join_request.member.id != x_user_id:
            logger.warning(
                "unauthorized_join_request_cancellation",
                join_request_id=str(join_request_id),
                user_id=str(x_user_id),
                member_id=str(join_request.member.id),
            )
            raise HTTPException(
                status_code=403,
                detail="You can only cancel your own join requests",
            )

        try:
            await service.cancel_join_request(join_request_id)
            logger.info("join_request_cancelled", join_request_id=str(join_request_id))
        except JoinRequestNotFoundError:
            logger.warning(
                "join_request_not_found", join_request_id=str(join_request_id)
            )
            raise HTTPException(status_code=404, detail="JoinRequest not found")
        except Exception as e:
            logger.error(
                "join_request_cancellation_failed",
                join_request_id=str(join_request_id),
                error=str(e),
            )
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            raise HTTPException(status_code=500, detail="Failed to cancel join request")

    @router.put("/join_requests/{join_request_id}", status_code=204)
    async def decide_join_request(
        join_request_id: uuid.UUID,
        request: DecisionRequest,
        x_user_id: Optional[uuid.UUID] = Header(None, alias="X-User-Id"),
    ):
        if x_user_id is None:
            raise HTTPException(status_code=401, detail="X-User-Id header missing")
        span = trace.get_current_span()
        span.set_attribute("join_request.id", str(join_request_id))
        span.set_attribute("decision", request.decision.value)

        logger.info(
            "join_request_decision_started",
            join_request_id=str(join_request_id),
            decision=request.decision.value,
        )

        try:
            if request.decision == DecisionEnum.ACCEPT:
                await service.accept_join_request(join_request_id)
            else:
                await service.reject_join_request(join_request_id)
            logger.info(
                "join_request_decision_completed",
                join_request_id=str(join_request_id),
                decision=request.decision.value,
            )
        except JoinRequestNotFoundError:
            logger.warning(
                "join_request_not_found", join_request_id=str(join_request_id)
            )
            raise HTTPException(status_code=404, detail="JoinRequest not found")
        except ParticipantAlreadyInTeam:
            logger.warning(
                "participant_already_in_team", join_request_id=str(join_request_id)
            )
            raise HTTPException(status_code=409, detail="Participant already in a team")
        except Exception as e:
            logger.error(
                "join_request_decision_failed",
                join_request_id=str(join_request_id),
                error=str(e),
            )
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            raise HTTPException(status_code=500, detail="Failed to decide join request")

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
