import uuid

from dataclasses import dataclass
import enum
from datetime import datetime


class TrackStatusEnum(str, enum.Enum):
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
