from datetime import datetime
from enum import Enum
from uuid import UUID
from dataclasses import dataclass, field
from src.models.event import Participant
from src.models.track import Role


class TeamStatusEnum(str, Enum):
    """Статусы команды"""

    DRAFT = "DRAFT"
    BUILDING = "BUILDING"
    FULL = "FULL"
    SUBMITTED = "SUBMITTED"
    VALIDATED = "VALIDATED"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    INVALID = "INVALID"


@dataclass
class Team:
    """Команда"""

    id: UUID
    track_id: UUID
    event_id: UUID
    owner: Participant
    members: list[Participant]
    required_roles: list[Role]
    name: str = ""
    description: str = ""
    status: TeamStatusEnum = TeamStatusEnum.DRAFT
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
