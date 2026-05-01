import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class EventStatusEnum(str, Enum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    FULL = "FULL"
    CLOSED = "CLOSED"


class EventTypeEnum(str, Enum):
    HACKATHON = "HACKATHON"
    PRACTICE = "PRACTICE"


@dataclass
class Event:
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
    faq: str
    status: EventStatusEnum


@dataclass
class Participant:
    id: uuid.UUID
    event_id: uuid.UUID

    name: str
    surname: str
    patronymic: str
    have_team: bool
    role_id: Optional[uuid.UUID] = None


@dataclass
class ParticipantEvent:
    id: uuid.UUID
    name: str
    description: str
    status: EventStatusEnum
    total_places: int
    current_participants: int
    tracks_count: int
    registration_start: datetime
    registration_end: datetime
    holding_start: datetime
    holding_end: datetime
    user_role: str
