from typing import Optional
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class TrackStatusEnum(str, Enum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    FULL = "FULL"
    CLOSED = "CLOSED"


@dataclass
class Role:
    id: uuid.UUID
    track_id: uuid.UUID
    name: str
    description: str
    count: int


@dataclass
class Track:
    id: uuid.UUID
    event_id: uuid.UUID

    name: str
    description: str

    max_team_count: int
    max_participants_count: int
    min_team_size: int
    max_team_size: int

    required_roles: list[Role]
    requirements: str

    status: TrackStatusEnum

    registration_deadline: datetime
