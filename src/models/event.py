import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


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
