import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

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
    required_roles: list[dict[str, Any]]  # JSONB
    status: TeamStatusEnum
    created_at: datetime
    updated_at: datetime

    def to_model(self, owner: Participant, members: list[Participant]) -> Team:
        roles = [
            Role(
                id=uuid.UUID(role["id"]) if role.get("id") else None,
                track_id=uuid.UUID(role["track_id"]) if role.get("track_id") else None,
                name=role.get("name", ""),
                description=role.get("description", ""),
                count=role.get("count", 0),
            )
            for role in self.required_roles
        ]

        return Team(
            id=self.id,
            track_id=self.track_id,
            event_id=self.event_id,
            owner=owner,
            members=members,
            required_roles=roles,
            name=self.name,
            description=self.description,
            status=self.status,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


@dataclass
class TeamMemberRow:
    team_id: uuid.UUID
    member_id: uuid.UUID
    joined_at: datetime
