import uuid
from typing import cast

from uuid_extensions import uuid7
from fastapi import APIRouter, HTTPException, Query

from src.controller.http.team.schemas import (
    CreateTeamRequest,
    UpdateTeamRequest,
    GetTeamResponse,
    GetTeamsResponse,
    TeamSubmitResponse,
)
from src.controller.http.team.protocols import TeamService
from src.service.errors import (
    TeamNotFoundError,
    ParticipantNotFoundError,
    EventNotFoundError,
)


def create_team_router(team_service: TeamService) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["team"])

    @router.post("/teams/{team_id}/submission", response_model=TeamSubmitResponse)
    async def post_team_submission(team_id: uuid.UUID):
        try:
            await team_service.team_submit(team_id)
            return TeamSubmitResponse(team_id=team_id)
        except TeamNotFoundError:
            raise HTTPException(status_code=404, detail="Team not found")

    @router.get("/teams/{id}", response_model=GetTeamResponse)
    async def get_teams_by_id(id: uuid.UUID):
        try:
            return GetTeamResponse.from_model(await team_service.get_team(id))
        except TeamNotFoundError:
            raise HTTPException(status_code=404, detail="Team not found")

    @router.get("/event/{event_id}/teams", response_model=GetTeamsResponse)
    async def get_event_teams(event_id: uuid.UUID):
        try:
            teams = await team_service.get_teams_by_event_id(event_id)
            return GetTeamsResponse(
                teams=[GetTeamResponse.from_model(t) for t in teams]
            )
        except EventNotFoundError:
            raise HTTPException(status_code=404, detail="Event not found")

    @router.get("/user/{user_id}/teams", response_model=GetTeamsResponse)
    async def get_user_teams(user_id: uuid.UUID):
        try:
            teams = await team_service.get_teams_by_user(user_id)
            return GetTeamsResponse(
                teams=[GetTeamResponse.from_model(t) for t in teams]
            )
        except ParticipantNotFoundError:
            raise HTTPException(status_code=404, detail="User not found")

    @router.get("/user/{user_id}/event/{event_id}/team", response_model=GetTeamResponse)
    async def get_user_event_team(user_id: uuid.UUID, event_id: uuid.UUID):
        try:
            team = await team_service.get_user_team_in_event(user_id, event_id)
            if team is None:
                raise HTTPException(status_code=404, detail="Team not found")
            return GetTeamResponse.from_model(team)
        except (EventNotFoundError, ParticipantNotFoundError):
            raise HTTPException(status_code=404, detail="Event or user not found")

    @router.delete("/teams/{id}", status_code=204)
    async def delete_teams_by_id(id: uuid.UUID):
        try:
            await team_service.delete_team(id)
        except TeamNotFoundError:
            raise HTTPException(status_code=404, detail="Team not found")

    @router.post("/teams", response_model=dict, status_code=201)
    async def post_teams(request: CreateTeamRequest):
        try:
            team_id = cast(uuid.UUID, uuid7())
            created_id = await team_service.create_team(request.to_model(team_id))
            return {"id": str(created_id)}
        except EventNotFoundError:
            raise HTTPException(status_code=404, detail="Event not found")
        except ParticipantNotFoundError:
            raise HTTPException(status_code=404, detail="Owner not found")

    @router.put("/teams/{team_id}", status_code=204)
    async def put_teams(team_id: uuid.UUID, request: UpdateTeamRequest):
        try:
            await team_service.update_team(request.to_model(team_id))
        except TeamNotFoundError:
            raise HTTPException(status_code=404, detail="Team not found")

    @router.delete("/team/member/{user_id}", status_code=204)
    async def delete_team_member(user_id: uuid.UUID, team_id: uuid.UUID = Query(...)):
        try:
            await team_service.kick_member(team_id, user_id)
        except TeamNotFoundError:
            raise HTTPException(status_code=404, detail="Team not found")
        except ParticipantNotFoundError:
            raise HTTPException(status_code=404, detail="User not found")

    return router
