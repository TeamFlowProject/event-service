import uuid
from dataclasses import dataclass
from datetime import datetime

from src.models.track import TrackStatusEnum


@dataclass
class TrackRow:
    id: uuid.UUID
    event_id: uuid.UUID
    name: str
    description: str
    max_team_count: int
    max_participants_count: int
    min_team_size: int
    max_team_size: int
    requirements: str
    status: TrackStatusEnum
    registration_deadline: datetime


@dataclass
class RoleRow:
    id: uuid.UUID
    track_id: uuid.UUID
    name: str
    description: str
    count: int
