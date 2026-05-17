import uuid
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DecisionEnum(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"


class CreateInvitationRequest(BaseModel):
    team_id: uuid.UUID
    owner_id: uuid.UUID
    member_id: uuid.UUID
    role_id: uuid.UUID
    description: str = Field(default="", max_length=5000)


class CreateJoinRequestRequest(BaseModel):
    team_id: uuid.UUID
    owner_id: uuid.UUID
    member_id: uuid.UUID
    role_id: uuid.UUID
    description: str = Field(default="", max_length=5000)


class DecisionRequest(BaseModel):
    decision: DecisionEnum


class Role(BaseModel):
    id: uuid.UUID
    track_id: uuid.UUID
    name: str
    description: str
    count: int


class Participant(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    name: str
    surname: str
    patronymic: str
    have_team: bool
    role_id: Optional[uuid.UUID] = None


class GetInvitationResponse(BaseModel):
    id: uuid.UUID
    team_id: uuid.UUID
    owner: Participant
    member: Participant
    role: Role
    description: str


class GetInvitationsResponse(BaseModel):
    invitations: list[GetInvitationResponse]


class GetJoinRequestResponse(BaseModel):
    id: uuid.UUID
    team_id: uuid.UUID
    owner: Participant
    member: Participant
    role: Role
    description: str


class GetJoinRequestsResponse(BaseModel):
    join_requests: list[GetJoinRequestResponse]
