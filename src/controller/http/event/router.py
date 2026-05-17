import uuid
from typing import Optional, cast
from datetime import datetime
from uuid_extensions import uuid7
from loguru import logger
from opentelemetry import trace
from fastapi import APIRouter, HTTPException

from src.controller.http.event.schemas import (
    CreatedResourceResponse,
    CreateEventRequest,
    CreateParticipantRequest,
    EventResponse,
    EventsPageResponse,
    Participant,
    ParticipantEvent,
    ParticipantEventsPageResponse,
    ParticipantsPageResponse,
    UpdateEventRequest,
    Event,
)
from src.service.event.service import EventService
from src.models.event import Event as EventModel, EventStatusEnum
from src.models.event import Participant as ParticipantModel
from src.service.errors import (
    EventNotFoundError,
    EventAlreadyExistsError,
    EventRepositoryError,
    PaginationError,
    ParticipantError,
    ParticipantNotFoundError,
)

tracer = trace.get_tracer(__name__)


def create_event_router(event_service: EventService) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["event"])

    @router.post("/events", response_model=CreatedResourceResponse, status_code=201)
    async def create_event(request: CreateEventRequest):
        event_id = cast(uuid.UUID, uuid7())
        span = trace.get_current_span()
        span.set_attribute("event.id", str(event_id))
        span.set_attribute("event.type", str(request.type))

        logger.info(
            "creating_event",
            event_id=str(event_id),
            event_name=request.name,
            event_type=str(request.type),
        )

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

        try:
            created_id = await event_service.create_event(event)
        except EventAlreadyExistsError:
            logger.warning("event_already_exists", event_id=str(event_id))
            raise HTTPException(status_code=409, detail="Event already exists")
        except (EventRepositoryError, Exception) as e:
            logger.error("event_creation_failed",
                         event_id=str(event_id), error=str(e))
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            raise HTTPException(
                status_code=500, detail="Failed to create event")

        logger.info("event_created_successfully", event_id=str(created_id))
        return CreatedResourceResponse(id=created_id)

    @router.get("/events/{event_id}", response_model=EventResponse)
    async def get_event_by_id(event_id: uuid.UUID):
        span = trace.get_current_span()
        span.set_attribute("event.id", str(event_id))

        logger.info("getting_event", event_id=str(event_id))

        try:
            event = await event_service.get_event_by_id(event_id)
        except EventNotFoundError:
            logger.warning("event_not_found", event_id=str(event_id))
            raise HTTPException(status_code=404, detail="Event not found")

        logger.info("event_received", event_id=str(event_id))
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

    @router.put("/events/{event_id}", response_model=EventResponse)
    async def update_event(request: UpdateEventRequest, event_id: uuid.UUID):
        span = trace.get_current_span()
        span.set_attribute("event.id", str(event_id))

        logger.info("updating_event", event_id=str(event_id))

        try:
            event = await event_service.get_event_by_id(event_id)
        except EventNotFoundError:
            logger.warning("event_not_found_for_update",
                           event_id=str(event_id))
            raise HTTPException(status_code=404, detail="Event not found")

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

        try:
            await event_service.update_event(updated_event)
        except EventNotFoundError:
            logger.warning("event_not_found_for_update",
                           event_id=str(event_id))
            raise HTTPException(status_code=404, detail="Event not found")
        except EventRepositoryError as e:
            logger.error("event_update_failed",
                         event_id=str(event_id), error=str(e))
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            raise HTTPException(
                status_code=500, detail="Failed to update event")

        logger.info("event_updated_successfully", event_id=str(event_id))
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

    @router.delete("/events/{event_id}", status_code=204)
    async def delete_event(event_id: uuid.UUID):
        span = trace.get_current_span()
        span.set_attribute("event.id", str(event_id))

        logger.info("deleting_event", event_id=str(event_id))

        try:
            await event_service.delete_event(event_id)
        except EventNotFoundError:
            logger.warning("event_not_found_for_delete",
                           event_id=str(event_id))
            raise HTTPException(status_code=404, detail="Event not found")
        except EventRepositoryError as e:
            logger.error("event_delete_failed",
                         event_id=str(event_id), error=str(e))
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            raise HTTPException(
                status_code=500, detail="Failed to delete event")

        logger.info("event_deleted_successfully", event_id=str(event_id))

    @router.get("/events", response_model=EventsPageResponse)
    async def get_events(
        event_id: Optional[uuid.UUID] = None,
        offset: Optional[int] = None,
        limit: int = 10,
    ):
        span = trace.get_current_span()
        span.set_attribute("pagination.limit", limit)
        if event_id:
            span.set_attribute("pagination.cursor_id", str(event_id))
        if offset is not None:
            span.set_attribute("pagination.offset", offset)

        logger.info(
            "getting_events_page",
            cursor_id=str(event_id) if event_id else None,
            offset=offset,
            limit=limit,
        )

        try:
            events, next_cursor = await event_service.get_events_page(
                event_id=event_id, offset=offset, limit=limit
            )
        except PaginationError as e:
            logger.warning("events_pagination_error", error=str(e))
            raise HTTPException(status_code=400, detail=str(e))
        except EventRepositoryError as e:
            logger.error("events_fetch_failed", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to get events")

        logger.info("events_page_received", count=len(events))
        items = [
            Event(
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
            for e in events
        ]
        return EventsPageResponse(items=items, next_cursor=next_cursor)

    @router.post(
        "/events/{event_id}/participants",
        response_model=CreatedResourceResponse,
        status_code=201,
    )
    async def create_participant(
        event_id: uuid.UUID, request: CreateParticipantRequest
    ):
        participant_id = cast(uuid.UUID, uuid7())
        span = trace.get_current_span()
        span.set_attribute("event.id", str(event_id))
        span.set_attribute("participant.id", str(participant_id))

        logger.info(
            "adding_participant",
            event_id=str(event_id),
            participant_id=str(participant_id),
        )

        participant = ParticipantModel(
            id=participant_id,
            event_id=event_id,
            name=request.name,
            surname=request.surname,
            patronymic=request.patronymic,
            have_team=request.have_team,
        )

        try:
            await event_service.add_participant(event_id, participant)
        except EventNotFoundError:
            logger.warning("event_not_found_for_participant",
                           event_id=str(event_id))
            raise HTTPException(status_code=404, detail="Event not found")
        except ParticipantError as e:
            logger.warning(
                "participant_add_failed",
                event_id=str(event_id),
                participant_id=str(participant_id),
                error=str(e),
            )
            raise HTTPException(status_code=400, detail=str(e))
        except EventRepositoryError as e:
            logger.error(
                "participant_add_error",
                event_id=str(event_id),
                participant_id=str(participant_id),
                error=str(e),
            )
            raise HTTPException(
                status_code=500, detail="Failed to add participant")

        logger.info(
            "participant_added_successfully",
            event_id=str(event_id),
            participant_id=str(participant_id),
        )
        return CreatedResourceResponse(id=participant_id)

    @router.get(
        "/events/{event_id}/participants", response_model=ParticipantsPageResponse
    )
    async def get_participants(
        event_id: uuid.UUID,
        participant_id: Optional[uuid.UUID] = None,
        offset: Optional[int] = None,
        limit: int = 10,
    ):
        span = trace.get_current_span()
        span.set_attribute("event.id", str(event_id))
        span.set_attribute("pagination.limit", limit)

        logger.info(
            "getting_participants",
            event_id=str(event_id),
            cursor_id=str(participant_id) if participant_id else None,
            offset=offset,
            limit=limit,
        )

        try:
            participants, next_cursor = await event_service.get_participants(
                event_id=event_id,
                participant_id=participant_id,
                offset=offset,
                limit=limit,
            )
        except EventNotFoundError:
            logger.warning("event_not_found_for_participants",
                           event_id=str(event_id))
            raise HTTPException(status_code=404, detail="Event not found")
        except ParticipantNotFoundError:
            logger.warning("participant_not_found", event_id=str(event_id))
            raise HTTPException(
                status_code=404, detail="Participant not found")
        except PaginationError as e:
            logger.warning("participants_pagination_error", error=str(e))
            raise HTTPException(status_code=400, detail=str(e))
        except EventRepositoryError as e:
            logger.error("participants_fetch_failed",
                         event_id=str(event_id), error=str(e))
            raise HTTPException(
                status_code=500, detail="Failed to get participants")

        logger.info("participants_received", event_id=str(
            event_id), count=len(participants))
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

    @router.get(
        "/participants/{participant_id}/events",
        response_model=ParticipantEventsPageResponse,
    )
    async def get_participant_events(
        participant_id: uuid.UUID,
        event_id: Optional[uuid.UUID] = None,
        offset: Optional[int] = None,
        limit: int = 10,
    ):
        span = trace.get_current_span()
        span.set_attribute("participant.id", str(participant_id))
        span.set_attribute("pagination.limit", limit)

        logger.info(
            "getting_participant_events",
            participant_id=str(participant_id),
            cursor_id=str(event_id) if event_id else None,
            offset=offset,
            limit=limit,
        )

        try:
            events, next_cursor = await event_service.get_participant_events(
                participant_id=participant_id,
                event_id=event_id,
                offset=offset,
                limit=limit,
            )
        except PaginationError as e:
            logger.warning("participant_events_pagination_error", error=str(e))
            raise HTTPException(status_code=400, detail=str(e))
        except ParticipantNotFoundError:
            logger.warning("participant_not_found",
                           participant_id=str(participant_id))
            raise HTTPException(
                status_code=404, detail="Participant not found")
        except EventNotFoundError:
            logger.warning("event_not_found",
                           participant_id=str(participant_id))
            raise HTTPException(status_code=404, detail="Event not found")
        except EventRepositoryError as e:
            logger.error(
                "participant_events_fetch_failed",
                participant_id=str(participant_id),
                error=str(e),
            )
            raise HTTPException(status_code=500, detail="Failed to get events")

        logger.info(
            "participant_events_received",
            participant_id=str(participant_id),
            count=len(events),
        )
        items = [
            ParticipantEvent(
                id=e.id,
                name=e.name,
                description=e.description,
                status=e.status,
                total_places=e.total_places,
                current_participants=e.current_participants,
                tracks_count=e.tracks_count,
                registration_start=e.registration_start,
                registration_end=e.registration_end,
                holding_start=e.holding_start,
                holding_end=e.holding_end,
                user_role=e.user_role,
            )
            for e in events
        ]
        return ParticipantEventsPageResponse(items=items, next_cursor=next_cursor)

    return router
