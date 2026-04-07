from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from typing import List, Optional


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


# HTTP DTOs
@dataclass
class CreateTeamRequestDTO:
    name: str
    description: str
    track_id: UUID
    event_id: UUID
    owner_id: UUID
    required_roles: List[Role]


@dataclass
class UpdateTeamRequestDTO:
    name: str | None = None
    description: str | None = None
    required_roles: List[Role] | None = None


@dataclass
class TeamSubmissionRequestDTO:
    team_id: UUID
    submission_url: str


@dataclass
class TeamResponseDTO:
    id: UUID
    name: str
    description: str
    track_id: UUID
    event_id: UUID
    owner_id: UUID
    member_ids: List[UUID]
    required_roles: List[Role]
    status: TeamStatusEnum
    members_count: int
    created_at: datetime
    updated_at: datetime