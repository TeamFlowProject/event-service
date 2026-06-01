import uuid
from typing import Optional, cast
from uuid_extensions import uuid7
from loguru import logger
from opentelemetry import trace
from fastapi import APIRouter, Header, HTTPException

from src.controller.http.track.schemas import (
    CreateTrackRequest,
    TrackStatus,
    UpdateTrackRequest,
    Track,
    Role,
)
from src.models.track import Track as TrackModel, Role as RoleModel, TrackStatusEnum
from src.controller.http.track.protocols import TrackService
from src.service.errors import (
    TrackNotFoundError,
    EventNotFoundError,
)

tracer = trace.get_tracer(__name__)


def create_track_router(track_service: TrackService) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["track"])

    @router.post("/track", response_model=dict, status_code=201)
    async def create_track(
        request: CreateTrackRequest,
        x_user_id: Optional[uuid.UUID] = Header(None, alias="X-User-Id"),
    ):
        if x_user_id is None:
            raise HTTPException(status_code=401, detail="X-User-Id header missing")
        track_id = cast(uuid.UUID, uuid7())
        span = trace.get_current_span()
        span.set_attribute("track.id", str(track_id))
        span.set_attribute("event.id", str(request.event_id))

        logger.info(
            "creating_track",
            track_id=str(track_id),
            event_id=str(request.event_id),
            track_name=request.name,
        )

        track = _request_to_model(request, track_id)

        try:
            created_id = await track_service.create_track(track)
        except EventNotFoundError:
            logger.warning(
                "event_not_found_for_track",
                event_id=str(request.event_id),
            )
            raise HTTPException(status_code=404, detail="Event not found")

        logger.info("track_created_successfully", track_id=str(created_id))
        return {"id": str(created_id)}

    @router.get("/track/{track_id}", response_model=Track)
    async def get_track(
        track_id: uuid.UUID,
        x_user_id: Optional[uuid.UUID] = Header(None, alias="X-User-Id"),
    ):
        if x_user_id is None:
            raise HTTPException(status_code=401, detail="X-User-Id header missing")
        span = trace.get_current_span()
        span.set_attribute("track.id", str(track_id))

        logger.info("getting_track", track_id=str(track_id))

        try:
            track = await track_service.get_track(track_id)
        except TrackNotFoundError:
            logger.warning("track_not_found", track_id=str(track_id))
            raise HTTPException(status_code=404, detail="Track not found")

        logger.info("track_received", track_id=str(track_id))
        return _track_to_response(track)

    @router.get("/event/{event_id}/tracks", response_model=list[Track])
    async def get_tracks_by_event_id(
        event_id: uuid.UUID,
        x_user_id: Optional[uuid.UUID] = Header(None, alias="X-User-Id"),
    ):
        if x_user_id is None:
            raise HTTPException(status_code=401, detail="X-User-Id header missing")
        span = trace.get_current_span()
        span.set_attribute("event.id", str(event_id))

        logger.info("getting_tracks_by_event", event_id=str(event_id))

        try:
            tracks = await track_service.get_tracks_by_event_id(event_id)
        except EventNotFoundError:
            logger.warning("event_not_found_for_tracks", event_id=str(event_id))
            raise HTTPException(status_code=404, detail="Event not found")

        logger.info(
            "tracks_received",
            event_id=str(event_id),
            count=len(tracks),
        )
        return [_track_to_response(track) for track in tracks]

    @router.put("/track/{track_id}", status_code=204)
    async def update_track(
        track_id: uuid.UUID,
        request: UpdateTrackRequest,
        x_user_id: Optional[uuid.UUID] = Header(None, alias="X-User-Id"),
    ):
        if x_user_id is None:
            raise HTTPException(status_code=401, detail="X-User-Id header missing")
        span = trace.get_current_span()
        span.set_attribute("track.id", str(track_id))

        logger.info("updating_track", track_id=str(track_id))

        track = _request_to_model(request, track_id)

        try:
            await track_service.update_track(track)
        except TrackNotFoundError:
            logger.warning("track_not_found_for_update", track_id=str(track_id))
            raise HTTPException(status_code=404, detail="Track not found")

        logger.info("track_updated_successfully", track_id=str(track_id))

    @router.delete("/track/{track_id}", status_code=204)
    async def delete_track(
        track_id: uuid.UUID,
        x_user_id: Optional[uuid.UUID] = Header(None, alias="X-User-Id"),
    ):
        if x_user_id is None:
            raise HTTPException(status_code=401, detail="X-User-Id header missing")
        span = trace.get_current_span()
        span.set_attribute("track.id", str(track_id))

        logger.info("deleting_track", track_id=str(track_id))

        try:
            await track_service.delete_track(track_id)
        except TrackNotFoundError:
            logger.warning("track_not_found_for_delete", track_id=str(track_id))
            raise HTTPException(status_code=404, detail="Track not found")

        logger.info("track_deleted_successfully", track_id=str(track_id))

    return router


def _request_to_model(
    request: CreateTrackRequest | UpdateTrackRequest,
    track_id: uuid.UUID,
) -> TrackModel:
    roles = [
        RoleModel(
            id=getattr(role, "id", None) or cast(uuid.UUID, uuid7()),
            track_id=track_id,
            name=role.name,
            description=role.description,
            count=role.count,
        )
        for role in request.required_roles
    ]
    return TrackModel(
        id=track_id,
        event_id=request.event_id,
        name=request.name,
        description=request.description,
        max_team_count=request.max_team_count,
        max_participants_count=request.max_participant_count,
        min_team_size=request.min_team_size,
        max_team_size=request.max_team_size,
        required_roles=roles,
        requirements=request.requirements,
        status=TrackStatusEnum(request.status),
        registration_deadline=request.registration_deadline,
    )


def _track_to_response(track: TrackModel) -> Track:
    return Track(
        id=track.id,
        event_id=track.event_id,
        name=track.name,
        description=track.description,
        max_team_count=track.max_team_count,
        max_participant_count=track.max_participants_count,
        min_team_size=track.min_team_size,
        max_team_size=track.max_team_size,
        required_roles=[
            Role(
                id=role.id,
                name=role.name,
                description=role.description,
                count=role.count,
            )
            for role in track.required_roles
        ],
        requirements=track.requirements,
        status=TrackStatus(track.status.value),
        registration_deadline=track.registration_deadline,
    )
