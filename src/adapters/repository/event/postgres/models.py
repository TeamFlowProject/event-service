import uuid
from dataclasses import dataclass
from datetime import datetime

from src.models.event import (
    Event,
    EventStatusEnum,
    EventTypeEnum,
    Participant,
    ParticipantEvent,
)
from src.models.track import Role


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


@dataclass
class ParticipantEventRow:
    id: uuid.UUID
    name: str
    description: str
    registration_start: datetime
    registration_end: datetime
    holding_start: datetime
    holding_end: datetime
    status: EventStatusEnum
    total_places: int
    current_participants: int
    tracks_count: int
    user_role_id: uuid.UUID | None
    user_role_track_id: uuid.UUID | None
    user_role_name: str | None
    user_role_description: str | None
    user_role_count: int | None
    event_first_track_id: uuid.UUID | None

    def _user_role(self) -> Role | None:
        if self.user_role_id is not None and self.user_role_track_id is not None:
            return Role(
                id=self.user_role_id,
                track_id=self.user_role_track_id,
                name=self.user_role_name or "",
                description=self.user_role_description or "",
                count=int(self.user_role_count or 0),
            )
        return None

    def to_model(self) -> ParticipantEvent:
        return ParticipantEvent(
            id=self.id,
            name=self.name,
            description=self.description,
            registration_start=self.registration_start,
            registration_end=self.registration_end,
            holding_start=self.holding_start,
            holding_end=self.holding_end,
            status=self.status,
            total_places=self.total_places,
            current_participants=self.current_participants,
            tracks_count=self.tracks_count,
            user_role=self._user_role(),
        )
