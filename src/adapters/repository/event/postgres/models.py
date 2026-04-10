import uuid
from dataclasses import dataclass
from datetime import datetime

from src.models.event import EventTypeEnum, EventStatusEnum


@dataclass
class EventRow:
    id: uuid.UUID
    name: str
    description: str
    type: EventTypeEnum

    registration_start: datetime
    registration_end: datetime
    holding_start: datetime
    holding_end: datetime
    created_at: datetime

    organizers: list[str]
    rules: str
    FAQ: str
    status: EventStatusEnum


@dataclass
class ParticipantRow:
    id: uuid.UUID
    name: str
    surname: str
    patronymic: str


@dataclass
class EventParticipantRow:
    id: uuid.UUID
    event_id: uuid.UUID
    participant_id: uuid.UUID
    have_team: bool
    registered_at: datetime
