import uuid
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException
from uuid_extensions import uuid7

from src.controller.http.event.schemas import (
    CreatedResourceResponse,
    CreateEventRequest,
    EventResponse,
    EventsPageResponse,
    Participant,
    ParticipantsPageResponse,
    UpdateEventRequest,
    Event,
)
from src.service.event.service import EventService
from src.models.event import Event as EventModel, EventStatusEnum
from src.service.errors import EventNotFoundError, PaginationError, ParticipantNotFoundError


def create_event_router(event_service: EventService) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["event"])

    @router.post("/events", response_model=CreatedResourceResponse,  status_code=201)
    async def create_event(request: CreateEventRequest):
        event_id = uuid7()
        event = EventModel(
            id=event_id,
            name=request.name,
            type=request.type,
            description=request.description,
            registration_start=request.registration_start,
            registration_end=request.registration_end,
            holding_start=request.holding_start,
            holding_end=request.holding_end,
            created_at=datetime.now(),
            organizers=request.organizers,
            rules=request.rules,
            faq=request.faq,
            status=EventStatusEnum.DRAFT,
        )
        created_id = await event_service.create_event(event)
        return CreatedResourceResponse(id=created_id)

    @router.get("/events/{event_id}", response_model=EventResponse)
    async def get_event_by_id(event_id: uuid.UUID):
        try:
            event = await event_service.get_event_by_id(event_id)
            return EventResponse(
                id=event.id,
                name=event.name,
                type=event.type,
                description=event.description,
                registration_start=event.registration_start,
                registration_end=event.registration_end,
                holding_start=event.holding_start,
                holding_end=event.holding_end,
                created_at=event.created_at,
                organizers=event.organizers,
                rules=event.rules,
                faq=event.faq,
                status=event.status,
            )
        except EventNotFoundError:
            raise HTTPException(status_code=404, detail="Event not found")

    @router.put("/events/{event_id}", response_model=EventResponse)
    async def update_event(request: UpdateEventRequest, event_id: uuid.UUID):
        try:
            event = await event_service.get_event_by_id(event_id)
            updated_event = EventModel(
                id=event_id,
                name=request.name or event.name,
                type=request.type or event.type,
                description=request.description or event.description,
                registration_start=request.registration_start or event.registration_start,
                registration_end=request.registration_end or event.registration_end,
                holding_start=request.holding_start or event.holding_start,
                holding_end=request.holding_end or event.holding_end,
                created_at=event.created_at,
                organizers=request.organizers or event.organizers,
                rules=request.rules or event.rules,
                faq=request.faq or event.faq,
                status=request.status or event.status,
            )
            await event_service.update_event(updated_event)
            return EventResponse(
                id=updated_event.id,
                name=updated_event.name,
                type=updated_event.type,
                description=updated_event.description,
                registration_start=updated_event.registration_start,
                registration_end=updated_event.registration_end,
                holding_start=updated_event.holding_start,
                holding_end=updated_event.holding_end,
                created_at=updated_event.created_at,
                organizers=updated_event.organizers,
                rules=updated_event.rules,
                faq=updated_event.faq,
                status=updated_event.status,
            )
        except EventNotFoundError:
            raise HTTPException(status_code=404, detail="Event not found")

    @router.delete("/events/{event_id}", status_code=204)
    async def delete_event(event_id: uuid.UUID):
        try:
            await event_service.delete_event(event_id)
        except EventNotFoundError:
            raise HTTPException(status_code=404, detail="Event not found")

    @router.get("/events", response_model=EventsPageResponse)
    async def get_events(event_id: Optional[uuid.UUID] = None, offset: Optional[int] = None, limit: int = 10):
        try:
            events, next_cursor = await event_service.get_events_page(
                event_id=event_id,
                offset=offset,
                limit=limit
            )
        except PaginationError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        items = [Event(
                id=e.id,
                name=e.name,
                description=e.description,
                type=e.type,
                registration_start=e.registration_start,
                registration_end=e.registration_end,
                holding_start=e.holding_start,
                holding_end=e.holding_end,
                created_at=e.created_at,
                organizers=e.organizers,
                rules=e.rules,
                faq=e.faq,
                status=e.status,
                )
                for e in events]

        return EventsPageResponse(
            items=items,
            next_cursor=next_cursor
        )


    @router.get("/events/{event_id}/participants", response_model=ParticipantsPageResponse)
    async def get_participants(
        event_id: uuid.UUID,
        participant_id: Optional[uuid.UUID] = None,
        offset: Optional[int] = None,
        limit: int = 10,
    ):
        try:
            participants, next_cursor = await event_service.get_participants(
                event_id=event_id,
                participant_id=participant_id,
                offset=offset,
                limit=limit,
            )

            items = [
                Participant(
                    id=p.id,
                    event_id=p.event_id,
                    name=p.name,
                    surname=p.surname,
                    patronymic=p.patronymic,
                    have_team=p.have_team,
                )
                for p in participants
            ]
            return ParticipantsPageResponse(items=items, next_cursor=next_cursor)
        except EventNotFoundError:
            raise HTTPException(status_code=404, detail="Event not found")
        except ParticipantNotFoundError:
            raise HTTPException(status_code=404, detail="Participant not found")
        except PaginationError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    return router
