import uuid

from pydantic import BaseModel
from datetime import datetime
from src.models.event import Event, Participant, EventTypeEnum, EventStatusEnum


class EventDTO(BaseModel):
    id: str
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

    @classmethod
    def from_model(cls, model: Event) -> "EventDTO":
        return cls(
            id=str(model.id),
            name=model.name,
            description=model.description,
            type=model.type,
            registration_start=model.registration_start,
            registration_end=model.registration_end,
            holding_start=model.holding_start,
            holding_end=model.holding_end,
            created_at=model.created_at,
            organizers=model.organizers,
            rules=model.rules,
            faq=model.faq,
            status=model.status,
        )


class ParticipantDTO(BaseModel):
    id: str
    event_id: str

    name: str
    surname: str
    patronymic: str
    have_team: bool

    @classmethod
    def from_model(cls, model: Participant) -> "ParticipantDTO":
        return cls(
            id=str(model.id),
            event_id=str(model.event_id),
            name=model.name,
            surname=model.surname,
            patronymic=model.patronymic,
            have_team=model.have_team,
        )


class EventCreated(EventDTO): ...


class EventUpdated(EventDTO): ...


class EventDeleted(BaseModel):
    id: str

    @classmethod
    def from_model(cls, event_id: uuid.UUID) -> "EventDeleted":
        return cls(id=str(event_id))


class AddParticipant(BaseModel):
    event: Event
    participant_id: str

    @classmethod
    def from_model(cls, event: Event, participant_id: uuid.UUID) -> "AddParticipant":
        return cls(
            event=event,
            participant_id=str(participant_id),
        )
