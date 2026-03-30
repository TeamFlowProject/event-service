from fastapi import APIRouter

from src.service.track_service import TrackService


def create_track_router(track_service: TrackService) -> APIRouter: ...
