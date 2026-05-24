from datetime import datetime

from pydantic import BaseModel

from src.adapters.clients.dto.invitation import Role
from src.models.event import Participant as ParticipantModel
from src.models.team import Team, TeamStatusEnum


class TeamEventDTO(BaseModel):
    id: str
    name: str
    description: str
    track_id: str
    event_id: str
    owner_id: str
    required_roles: list[Role]
    status: TeamStatusEnum
    created_at: datetime
    updated_at: datetime

    @classmethod
    def _base_fields(cls, model: Team) -> dict:
        return {
            "id": str(model.id),
            "name": model.name,
            "description": model.description,
            "track_id": str(model.track_id),
            "event_id": str(model.event_id),
            "owner_id": str(model.owner.id),
            "required_roles": [Role.from_model(r) for r in model.required_roles],
            "status": model.status,
            "created_at": model.created_at,
            "updated_at": model.updated_at,
        }

    @classmethod
    def from_model(cls, model: Team) -> "TeamEventDTO":
        return cls(**cls._base_fields(model))


class TeamWithMembersDTO(TeamEventDTO):
    member_ids: list[str]

    @classmethod
    def from_model(cls, model: Team) -> "TeamWithMembersDTO":
        return cls(
            **cls._base_fields(model),
            member_ids=[str(m.id) for m in model.members],
        )


class TeamCreated(TeamWithMembersDTO): ...


class TeamUpdated(TeamEventDTO): ...


class TeamDeleted(TeamWithMembersDTO): ...


class TeamSubmitted(TeamWithMembersDTO): ...


class MemberTeamEventDTO(TeamEventDTO):
    member_id: str

    @classmethod
    def from_team_and_member(
        cls, team: Team, member: ParticipantModel
    ) -> "MemberTeamEventDTO":
        return cls(
            **cls._base_fields(team),
            member_id=str(member.id),
        )


class MemberLeft(MemberTeamEventDTO): ...


class MemberKicked(MemberTeamEventDTO): ...
