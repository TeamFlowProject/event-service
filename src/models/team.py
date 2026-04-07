from datetime import datetime
from enum import Enum
from uuid import UUID
from dataclasses import dataclass, field


class TeamStatusEnum(str, Enum):
    """Статусы команды"""

    DRAFT = "draft"
    BUILDING = "building"
    FULL = "full"
    SUBMITTED = "submitted"
    VALIDATED = "validated"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    INVALID = "invalid"


@dataclass
class Role:
    """Роль в команде"""

    id: UUID
    name: str = ""
    description: str = ""
    count: int = 1


@dataclass
class User:
    """Пользователь системы"""

    id: UUID
    name: str = ""
    surname: str = ""
    patronymic: str = ""


@dataclass
class Team:
    """Команда"""

    id: UUID
    track_id: UUID
    event_id: UUID
    owner_id: UUID
    member_ids: list[UUID]
    required_roles: list[Role]
    name: str = ""
    description: str = ""
    status: TeamStatusEnum = TeamStatusEnum.DRAFT
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
