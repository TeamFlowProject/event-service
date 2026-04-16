import uuid
from dataclasses import dataclass
from datetime import datetime

from src.models.event import Event, Participant, EventTypeEnum, EventStatusEnum


@dataclass
class EventRow:
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

    def to_model(self) -> Event:
        return Event(
            id=self.id,
            name=self.name,
            description=self.description,
            type=self.type,
            registration_start=self.registration_start,
            registration_end=self.registration_end,
            holding_start=self.holding_start,
            holding_end=self.holding_end,
            created_at=self.created_at,
            organizers=self.organizers,
            rules=self.rules,
            faq=self.faq,
            status=self.status,
        )


@dataclass
class ParticipantRow:
    id: uuid.UUID
    name: str
    surname: str
    patronymic: str
    have_team: bool

    def to_model(self, event_id: uuid.UUID) -> Participant:
        return Participant(
            id=self.id,
            event_id=event_id,
            name=self.name,
            surname=self.surname,
            patronymic=self.patronymic,
            have_team=self.have_team,
        )
