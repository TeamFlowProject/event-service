import uuid
from typing import cast

from uuid_extensions import uuid7
from loguru import logger
from opentelemetry import trace
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

tracer = trace.get_tracer(__name__)


def create_team_router(team_service: TeamService) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["team"])

    @router.post("/teams/{team_id}/submission", response_model=TeamSubmitResponse)
    async def post_team_submission(team_id: uuid.UUID):
        span = trace.get_current_span()
        span.set_attribute("team.id", str(team_id))

        logger.info("team_submission_started", team_id=str(team_id))

        try:
            await team_service.team_submit(team_id)
            logger.info("team_submission_completed", team_id=str(team_id))
            return TeamSubmitResponse(team_id=team_id)
        except TeamNotFoundError:
            logger.warning("team_not_found", team_id=str(team_id))
            raise HTTPException(status_code=404, detail="Team not found")
        except Exception as e:
            logger.error("team_submission_failed",
                         team_id=str(team_id), error=str(e))
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            raise HTTPException(
                status_code=500, detail="Failed to submit team")

    @router.get("/teams/{id}", response_model=GetTeamResponse)
    async def get_teams_by_id(id: uuid.UUID):
        span = trace.get_current_span()
        span.set_attribute("team.id", str(id))

        logger.info("team_fetch_started", team_id=str(id))

        try:
            team = await team_service.get_team(id)
            logger.info("team_fetched", team_id=str(id))
            return GetTeamResponse.from_model(team)
        except TeamNotFoundError:
            logger.warning("team_not_found", team_id=str(id))
            raise HTTPException(status_code=404, detail="Team not found")
        except Exception as e:
            logger.error("team_fetch_failed", team_id=str(id), error=str(e))
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            raise HTTPException(status_code=500, detail="Failed to fetch team")

    @router.get("/event/{event_id}/teams", response_model=GetTeamsResponse)
    async def get_event_teams(event_id: uuid.UUID):
        span = trace.get_current_span()
        span.set_attribute("event.id", str(event_id))

        logger.info("event_teams_fetch_started", event_id=str(event_id))

        try:
            teams = await team_service.get_teams_by_event_id(event_id)
            logger.info("event_teams_fetched", event_id=str(
                event_id), teams_count=len(teams))
            return GetTeamsResponse(
                teams=[GetTeamResponse.from_model(t) for t in teams]
            )
        except EventNotFoundError:
            logger.warning("event_not_found", event_id=str(event_id))
            raise HTTPException(status_code=404, detail="Event not found")
        except Exception as e:
            logger.error("event_teams_fetch_failed",
                         event_id=str(event_id), error=str(e))
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            raise HTTPException(
                status_code=500, detail="Failed to fetch event teams")

    @router.get("/user/{user_id}/teams", response_model=GetTeamsResponse)
    async def get_user_teams(user_id: uuid.UUID):
        span = trace.get_current_span()
        span.set_attribute("user.id", str(user_id))

        logger.info("user_teams_fetch_started", user_id=str(user_id))

        try:
            teams = await team_service.get_teams_by_user(user_id)
            logger.info("user_teams_fetched", user_id=str(
                user_id), teams_count=len(teams))
            return GetTeamsResponse(
                teams=[GetTeamResponse.from_model(t) for t in teams]
            )
        except ParticipantNotFoundError:
            logger.warning("user_not_found", user_id=str(user_id))
            raise HTTPException(status_code=404, detail="User not found")
        except Exception as e:
            logger.error("user_teams_fetch_failed",
                         user_id=str(user_id), error=str(e))
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            raise HTTPException(
                status_code=500, detail="Failed to fetch user teams")

    @router.get("/user/{user_id}/event/{event_id}/team", response_model=GetTeamResponse)
    async def get_user_event_team(user_id: uuid.UUID, event_id: uuid.UUID):
        span = trace.get_current_span()
        span.set_attribute("user.id", str(user_id))
        span.set_attribute("event.id", str(event_id))

        logger.info("user_event_team_fetch_started",
                    user_id=str(user_id), event_id=str(event_id))

        try:
            team = await team_service.get_user_team_in_event(user_id, event_id)
            if team is None:
                logger.warning("user_event_team_not_found",
                               user_id=str(user_id), event_id=str(event_id))
                raise HTTPException(status_code=404, detail="Team not found")
            logger.info("user_event_team_fetched", user_id=str(
                user_id), event_id=str(event_id), team_id=str(team.id))
            return GetTeamResponse.from_model(team)
        except (EventNotFoundError, ParticipantNotFoundError):
            logger.warning("event_or_user_not_found", user_id=str(
                user_id), event_id=str(event_id))
            raise HTTPException(
                status_code=404, detail="Event or user not found")
        except Exception as e:
            logger.error("user_event_team_fetch_failed", user_id=str(
                user_id), event_id=str(event_id), error=str(e))
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            raise HTTPException(
                status_code=500, detail="Failed to fetch user event team")

    @router.delete("/teams/{id}", status_code=204)
    async def delete_teams_by_id(id: uuid.UUID):
        span = trace.get_current_span()
        span.set_attribute("team.id", str(id))

        logger.info("team_deletion_started", team_id=str(id))

        try:
            await team_service.delete_team(id)
            logger.info("team_deleted", team_id=str(id))
        except TeamNotFoundError:
            logger.warning("team_not_found", team_id=str(id))
            raise HTTPException(status_code=404, detail="Team not found")
        except Exception as e:
            logger.error("team_deletion_failed", team_id=str(id), error=str(e))
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            raise HTTPException(
                status_code=500, detail="Failed to delete team")

    @router.post("/teams", response_model=dict, status_code=201)
    async def post_teams(request: CreateTeamRequest):
        team_id = cast(uuid.UUID, uuid7())
        span = trace.get_current_span()
        span.set_attribute("team.id", str(team_id))
        span.set_attribute("event.id", str(request.event_id))

        logger.info("team_creation_started", team_id=str(
            team_id), event_id=str(request.event_id))

        try:
            created_id = await team_service.create_team(request.to_model(team_id))
            logger.info("team_created", team_id=str(created_id))
            return {"id": str(created_id)}
        except EventNotFoundError:
            logger.warning("event_not_found", event_id=str(request.event_id))
            raise HTTPException(status_code=404, detail="Event not found")
        except ParticipantNotFoundError:
            logger.warning("owner_not_found", team_id=str(
                team_id), owner_id=str(request.owner_id))
            raise HTTPException(status_code=404, detail="Owner not found")
        except Exception as e:
            logger.error("team_creation_failed",
                         team_id=str(team_id), error=str(e))
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            raise HTTPException(
                status_code=500, detail="Failed to create team")

    @router.put("/teams/{team_id}", status_code=204)
    async def put_teams(team_id: uuid.UUID, request: UpdateTeamRequest):
        span = trace.get_current_span()
        span.set_attribute("team.id", str(team_id))

        logger.info("team_update_started", team_id=str(team_id))

        try:
            await team_service.update_team(request.to_model(team_id))
            logger.info("team_updated", team_id=str(team_id))
        except TeamNotFoundError:
            logger.warning("team_not_found", team_id=str(team_id))
            raise HTTPException(status_code=404, detail="Team not found")
        except Exception as e:
            logger.error("team_update_failed",
                         team_id=str(team_id), error=str(e))
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            raise HTTPException(
                status_code=500, detail="Failed to update team")

    @router.delete("/team/member/{user_id}", status_code=204)
    async def delete_team_member(user_id: uuid.UUID, team_id: uuid.UUID = Query(...)):
        span = trace.get_current_span()
        span.set_attribute("team.id", str(team_id))
        span.set_attribute("user.id", str(user_id))

        logger.info("team_member_removal_started",
                    team_id=str(team_id), user_id=str(user_id))

        try:
            await team_service.kick_member(team_id, user_id)
            logger.info("team_member_removed", team_id=str(
                team_id), user_id=str(user_id))
        except TeamNotFoundError:
            logger.warning("team_not_found", team_id=str(team_id))
            raise HTTPException(status_code=404, detail="Team not found")
        except ParticipantNotFoundError:
            logger.warning("user_not_found", user_id=str(user_id))
            raise HTTPException(status_code=404, detail="User not found")
        except Exception as e:
            logger.error("team_member_removal_failed", team_id=str(
                team_id), user_id=str(user_id), error=str(e))
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            raise HTTPException(
                status_code=500, detail="Failed to remove team member")

    return router
