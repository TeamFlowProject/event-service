from datetime import datetime
from enum import Enum
import uuid

from pydantic import BaseModel, Field, field_validator


class EventStatusEnum(str, Enum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    FULL = "FULL"
    CLOSED = "CLOSED"


class EventTypeEnum(str, Enum):
    HACKATHON = "HACKATHON"
    PRACTICE = "PRACTICE"


class _EventRequestBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: EventTypeEnum
    description: str = Field(min_length=1, max_length=1000)
    registration_start: datetime
    registration_end: datetime
    holding_start: datetime
    holding_end: datetime
    organizers: list[str] = Field(min_length=1)
    rules: str = Field(min_length=1, max_length=1000)
    faq: str = Field(min_length=1, max_length=1000)

    @field_validator("registration_end")
    @classmethod
    def validate_registration_date(cls, v: datetime, info) -> datetime:
        registration_start = info.data.get("registration_start")
        if registration_start is not None and v < registration_start:
            raise ValueError("registration_end must be >= registration_start")
        return v

    @field_validator("holding_end")
    @classmethod
    def validate_holding_date(cls, v: datetime, info) -> datetime:
        holding_start = info.data.get("holding_start")
        if holding_start is not None and v < holding_start:
            raise ValueError("holding_end must be >= holding_start")
        return v

    @field_validator("holding_start")
    @classmethod
    def validate_holding_vs_registration(cls, v: datetime, info) -> datetime:
        registration_end = info.data.get("registration_end")
        if registration_end is not None and v < registration_end:
            raise ValueError("holding_start must be >= registration_end")
        return v


class CreateEventRequest(_EventRequestBase):
    pass


class CreatedResourceResponse(BaseModel):
    id: uuid.UUID


class UpdateEventRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    type: EventTypeEnum | None = None
    description: str | None = Field(None, min_length=1, max_length=1000)
    registration_start: datetime | None = None
    registration_end: datetime | None = None
    holding_start: datetime | None = None
    holding_end: datetime | None = None
    organizers: list[str] | None = Field(None, min_length=1)
    rules: str | None = Field(None, min_length=1, max_length=1000)
    faq: str | None = Field(None, min_length=1, max_length=1000)
    status: EventStatusEnum | None = None


class Event(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    type: EventTypeEnum

    registration_start: datetime
    registration_end: datetime
    holding_start: datetime
    holding_end: datetime
    created_at: datetime

    organizers: list[str]
    rules: str
    faq: str
    status: EventStatusEnum


class EventsPageResponse(BaseModel):
    items: list[Event]
    next_cursor: uuid.UUID | int | None = None


class EventResponse(Event):
    pass


class Participant(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID

    name: str
    surname: str
    patronymic: str
    have_team: bool


class CreateParticipantRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    surname: str = Field(min_length=1, max_length=255)
    patronymic: str = Field(min_length=1, max_length=255)
    have_team: bool = False


class ParticipantsPageResponse(BaseModel):
    items: list[Participant]
    next_cursor: uuid.UUID | None = None
