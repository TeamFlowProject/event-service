from fastapi import APIRouter

from src.service.event.service import EventService


def create_event_router(event_service: EventService) -> APIRouter: ...
