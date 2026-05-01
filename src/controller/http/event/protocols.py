import uuid
from typing import Optional, Protocol

from src.models.event import (
    Event as EventModel,
    Participant as ParticipantModel,
    ParticipantEvent as ParticipantEventModel,
)


class EventService(Protocol):
    async def create_event(self, event: EventModel) -> uuid.UUID: ...

    async def update_event(self, event: EventModel) -> None: ...

    async def delete_event(self, event_id: uuid.UUID) -> None: ...

    async def get_event_by_id(self, event_id: uuid.UUID) -> EventModel: ...

    async def get_events_page(
        self,
        event_id: Optional[uuid.UUID] = None,
        offset: Optional[int] = None,
        limit: int = 10,
    ) -> tuple[list[EventModel], Optional[uuid.UUID]]: ...

    async def add_participant(
        self, event_id: uuid.UUID, participant: ParticipantModel
    ) -> None: ...

    async def get_participants(
        self,
        event_id: uuid.UUID,
        offset: Optional[int] = None,
        participant_id: Optional[uuid.UUID] = None,
        limit: int = 10,
    ) -> tuple[list[ParticipantModel], Optional[uuid.UUID]]: ...

    async def get_participant_events(
        self,
        participant_id: uuid.UUID,
        event_id: Optional[uuid.UUID] = None,
        offset: Optional[int] = None,
        limit: int = 10,
    ) -> tuple[list[ParticipantEventModel], Optional[uuid.UUID]]: ...
