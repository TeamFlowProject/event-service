# src/controller/http/team/router.py
import uuid
from datetime import datetime
from uuid_extensions import uuid7
from fastapi import APIRouter, HTTPException, Query, status

from src.controller.http.team.schemas import (
    CreateTeamRequest,
    UpdateTeamRequest,
    GetTeamResponse,
    GetTeamsResponse,
    TeamSubmitResponse,
)
from src.models.team import Team as TeamModel, TeamStatusEnum
from src.models.event import Participant
from src.controller.http.team.protocols import TeamService
from src.service.errors import (
    TeamNotFoundError,
    ParticipantNotFoundError,
)


def create_team_router(team_service: TeamService) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["team"])

    @router.post("/team/submission", response_model=TeamSubmitResponse)
    async def post_team_submission(team_id: uuid.UUID = Query(...)):
        try:
            await team_service.team_submit(team_id)
            return TeamSubmitResponse(team_id=team_id)
        except TeamNotFoundError:
            raise HTTPException(404, "Team not found")

    @router.get("/teams/{id}", response_model=GetTeamResponse)
    async def get_teams_by_id(id: uuid.UUID):
        try:
            team = await team_service.get_teams(id)
            return GetTeamResponse(
                id=team.id,
                name=team.name,
                description=team.description,
                track_id=team.track_id,
                event_id=team.event_id,
                owner_id=team.owner.id,
                member_ids=[member.id for member in team.members],
                required_roles=team.required_roles,
                status=team.status,
                created_at=team.created_at,
                updated_at=team.updated_at,
            )
        except TeamNotFoundError:
            raise HTTPException(404, "Team not found")

    @router.get("/event/{event_id}/teams", response_model=GetTeamsResponse)
    async def get_event_teams(event_id: uuid.UUID): ...

    @router.get("/user/{user_id}/teams", response_model=GetTeamsResponse)
    async def get_user_teams(user_id: uuid.UUID): ...

    @router.get(
        "/user/{user_id}/event/{event_id}/team", response_model=GetTeamResponse | None
    )
    async def get_user_event_team(user_id: uuid.UUID, event_id: uuid.UUID): ...

    @router.delete("/team", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_team_by_query(team_id: uuid.UUID = Query(...)):
        try:
            await team_service.delete_team(team_id)
        except TeamNotFoundError:
            raise HTTPException(404, "Team not found")

    @router.delete("/teams/{id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_teams_by_id(id: uuid.UUID):
        try:
            await team_service.delete_team(id)
        except TeamNotFoundError:
            raise HTTPException(404, "Team not found")

    @router.post("/teams", response_model=dict, status_code=status.HTTP_201_CREATED)
    async def post_teams(request: CreateTeamRequest):
        try:
            team_id = uuid7()
            # Создаем Participant для owner
            owner = Participant(
                id=request.owner_id,
                event_id=request.event_id,
                name="",
                surname="",
                patronymic="",
                have_team=False,
            )

            team = TeamModel(
                id=team_id,
                track_id=request.track_id,
                event_id=request.event_id,
                owner=owner,
                members=[],
                required_roles=[],
                name=request.name,
                description=request.description,
                status=TeamStatusEnum.DRAFT,
            )
            created_id = await team_service.create_team(team)
            return {"id": str(created_id)}
        except TeamNotFoundError:
            raise HTTPException(404, "Team not found")

    @router.put("/teams/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def put_teams(team_id: uuid.UUID, request: UpdateTeamRequest):
        try:
            existing = await team_service.get_teams(team_id)

            team = TeamModel(
                id=team_id,
                track_id=request.track_id or existing.track_id,
                event_id=existing.event_id,
                owner=existing.owner,
                members=existing.members,
                required_roles=existing.required_roles,
                name=request.name or existing.name,
                description=request.description or existing.description,
                status=existing.status,
                created_at=existing.created_at,
                updated_at=datetime.now(),
            )
            await team_service.update_team(team)
        except TeamNotFoundError:
            raise HTTPException(404, "Team not found")

    @router.delete("/team/member/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_team_member(user_id: uuid.UUID, team_id: uuid.UUID = Query(...)):
        try:
            await team_service.kick_member(team_id, user_id)
        except TeamNotFoundError:
            raise HTTPException(404, "Team not found")
        except ParticipantNotFoundError:
            raise HTTPException(404, "User not found")

    return router
