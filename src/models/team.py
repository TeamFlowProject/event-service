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
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    count: int = 1


@dataclass
class User:
    """Пользователь системы"""
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    surname: str = ""
    patronymic: str = ""


@dataclass
class Team:
    """Команда"""
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    track_id: UUID = field(default_factory=uuid4)
    event_id: UUID = field(default_factory=uuid4)
    owner_id: UUID = field(default_factory=uuid4)
    member_ids: List[UUID] = field(default_factory=list)
    required_roles: List[Role] = field(default_factory=list)
    status: TeamStatusEnum = TeamStatusEnum.DRAFT
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

