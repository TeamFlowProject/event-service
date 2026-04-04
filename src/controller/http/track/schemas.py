from datetime import datetime
from enum import Enum
import uuid

from pydantic import BaseModel, Field, field_validator


class TrackStatus(str, Enum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    FULL = "FULL"
    CLOSED = "CLOSED"


class RoleCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=1000)
    count: int = Field(ge=1)


class RoleUpdateRequest(BaseModel):
    id: uuid.UUID | None = None
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=1000)
    count: int = Field(ge=1)


class Role(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    count: int


class _TrackRequestBase(BaseModel):
    event_id: uuid.UUID
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=1000)
    max_team_count: int = Field(ge=1)
    max_participant_count: int = Field(ge=1)
    min_team_size: int = Field(ge=1)
    max_team_size: int = Field(ge=1)
    requirements: str = Field(min_length=1, max_length=5000)
    status: TrackStatus
    registration_deadline: datetime

    @field_validator("max_team_size")
    @classmethod
    def validate_team_size(cls, v: int, info) -> int:
        min_size = info.data.get("min_team_size")
        if min_size is not None and v < min_size:
            raise ValueError("max_team_size must be >= min_team_size")
        return v


class CreateTrackRequest(_TrackRequestBase):
    required_roles: list[RoleCreateRequest] = Field(min_length=1)


class UpdateTrackRequest(_TrackRequestBase):
    required_roles: list[RoleUpdateRequest] = Field(min_length=1)


class Track(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    name: str
    description: str
    max_team_count: int
    max_participant_count: int
    min_team_size: int
    max_team_size: int
    required_roles: list[Role]
    requirements: str
    status: TrackStatus
    registration_deadline: datetime
