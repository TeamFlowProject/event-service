# src/controller/http/team/schemas.py
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from src.models.team import TeamStatusEnum
from src.models.track import Role


class CreateTeamRequest(BaseModel):
    track_id: uuid.UUID
    event_id: uuid.UUID
    owner_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)


class UpdateTeamRequest(BaseModel):
    """PUT /teams - обновление команды"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    track_id: Optional[uuid.UUID] = None


class GetTeamResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    track_id: uuid.UUID
    event_id: uuid.UUID
    owner_id: uuid.UUID
    member_ids: list[uuid.UUID]
    required_roles: list[Role]
    status: TeamStatusEnum
    created_at: datetime
    updated_at: datetime


class GetTeamsResponse(BaseModel):
    teams: list[GetTeamResponse]


class TeamSubmitResponse(BaseModel):
    team_id: uuid.UUID
    message: str = "Submission successful"
