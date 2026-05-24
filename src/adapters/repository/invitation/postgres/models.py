import uuid
from dataclasses import dataclass
from typing import Optional

from src.models.event import Participant
from src.models.invitation import Invitation, JoinRequest
from src.models.track import Role


@dataclass
class InvitationRow:
    id: uuid.UUID
    team_id: uuid.UUID
    owner_id: uuid.UUID
    member_id: uuid.UUID
    role_id: uuid.UUID
    description: str

    def to_model(
        self, owner: Participant, member: Participant, role: Role
    ) -> Invitation:
        return Invitation(
            id=self.id,
            team_id=self.team_id,
            owner=owner,
            member=member,
            role=role,
            description=self.description,
        )


@dataclass
class JoinRequestRow:
    id: uuid.UUID
    team_id: uuid.UUID
    owner_id: uuid.UUID
    member_id: uuid.UUID
    role_id: uuid.UUID
    description: str

    def to_model(
        self, owner: Participant, member: Participant, role: Role
    ) -> JoinRequest:
        return JoinRequest(
            id=self.id,
            team_id=self.team_id,
            owner=owner,
            member=member,
            role=role,
            description=self.description,
        )


@dataclass
class ParticipantRow:
    id: uuid.UUID
    name: str
    surname: str
    patronymic: str
    have_team: bool
    event_id: uuid.UUID
    role_id: Optional[uuid.UUID] = None

    def to_model(self) -> Participant:
        return Participant(
            id=self.id,
            event_id=self.event_id,
            name=self.name,
            surname=self.surname,
            patronymic=self.patronymic,
            have_team=self.have_team,
            role_id=self.role_id,
        )


@dataclass
class RoleRow:
    id: uuid.UUID
    track_id: uuid.UUID
    name: str
    description: str
    count: int

    def to_model(self) -> Role:
        return Role(
            id=self.id,
            track_id=self.track_id,
            name=self.name,
            description=self.description,
            count=self.count,
        )


@dataclass
class TeamLookupRow:
    id: uuid.UUID
    track_id: uuid.UUID
    event_id: uuid.UUID
    owner_id: uuid.UUID
