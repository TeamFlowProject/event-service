import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.models.event import Participant
from src.models.team import Team, TeamStatusEnum
from src.models.track import Role


@dataclass
class TeamRow:
    id: uuid.UUID
    track_id: uuid.UUID
    event_id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    description: str
    status: TeamStatusEnum
    created_at: datetime
    updated_at: datetime

    def to_model(
        self,
        owner: Participant,
        members: list[Participant],
        required_roles: list[Role],
    ) -> Team:
        return Team(
            id=self.id,
            track_id=self.track_id,
            event_id=self.event_id,
            owner=owner,
            members=members,
            required_roles=required_roles,
            name=self.name,
            description=self.description,
            status=self.status,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


@dataclass
class TeamRoleRow:
    role_id: uuid.UUID
    track_id: uuid.UUID
    name: str
    description: str
    count: int
    required_count: int

    def to_model(self) -> Role:
        return Role(
            id=self.role_id,
            track_id=self.track_id,
            name=self.name,
            description=self.description,
            count=self.required_count,
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
class TeamMemberRow:
    team_id: uuid.UUID
    member_id: uuid.UUID
    role_id: uuid.UUID
    joined_at: datetime
