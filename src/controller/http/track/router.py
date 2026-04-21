import uuid

from fastapi import APIRouter, HTTPException

from src.controller.http.track.schemas import (
    CreateTrackRequest,
    TrackStatus,
    UpdateTrackRequest,
    Track,
    Role,
)
from src.models.track import Track as TrackModel, Role as RoleModel, TrackStatusEnum
from src.controller.http.track.protocols import TrackService
from src.service.errors import TrackNotFoundError, EventNotFoundError


def create_track_router(track_service: TrackService) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["track"])

    @router.post("/track", response_model=dict, status_code=201)
    async def create_track(request: CreateTrackRequest):
        try:
            track_id = uuid.uuid4()
            track = _request_to_model(request, track_id)
            created_id = await track_service.create_track(track)
            return {"id": str(created_id)}
        except EventNotFoundError:
            raise HTTPException(status_code=404, detail="Event not found")

    @router.get("/track/{track_id}", response_model=Track)
    async def get_track(track_id: uuid.UUID):
        try:
            track = await track_service.get_track(track_id)
            return _track_to_response(track)
        except TrackNotFoundError:
            raise HTTPException(status_code=404, detail="Track not found")

    @router.get("/event/{event_id}/tracks", response_model=list[Track])
    async def get_tracks_by_event_id(event_id: uuid.UUID):
        try:
            tracks = await track_service.get_tracks_by_event_id(event_id)
            return [_track_to_response(track) for track in tracks]
        except EventNotFoundError:
            raise HTTPException(status_code=404, detail="Event not found")

    @router.put("/track/{track_id}", status_code=204)
    async def update_track(track_id: uuid.UUID, request: UpdateTrackRequest):
        try:
            track = _request_to_model(request, track_id)
            await track_service.update_track(track)
        except TrackNotFoundError:
            raise HTTPException(status_code=404, detail="Track not found")

    @router.delete("/track/{track_id}", status_code=204)
    async def delete_track(track_id: uuid.UUID):
        try:
            await track_service.delete_track(track_id)
        except TrackNotFoundError:
            raise HTTPException(status_code=404, detail="Track not found")

    return router


def _request_to_model(
    request: CreateTrackRequest | UpdateTrackRequest,
    track_id: uuid.UUID,
) -> TrackModel:
    roles = [
        RoleModel(
            id=getattr(role, "id", None) or uuid.uuid4(),
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
