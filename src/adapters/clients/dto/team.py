from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from src.models.event import Participant as ParticipantModel
from src.models.team import Team, TeamStatusEnum
from src.models.track import Role as RoleModel


class ParticipantDTO(BaseModel):
    id: str
    name: str
    surname: str
    patronymic: str
    role_id: Optional[str] = None

    @classmethod
    def from_model(cls, model: ParticipantModel) -> "ParticipantDTO":
        return cls(
            id=str(model.id),
            name=model.name,
            surname=model.surname,
            patronymic=model.patronymic,
            role_id=str(model.role_id) if model.role_id else None,
        )


class RoleDTO(BaseModel):
    id: str
    track_id: str
    name: str
    description: str
    count: int

    @classmethod
    def from_model(cls, model: RoleModel) -> "RoleDTO":
        return cls(
            id=str(model.id),
            track_id=str(model.track_id),
            name=model.name,
            description=model.description,
            count=model.count,
        )


class TeamEventDTO(BaseModel):
    id: str
    track_id: str
    event_id: str
    owner: ParticipantDTO
    required_roles: list[RoleDTO]
    name: str
    description: str
    status: TeamStatusEnum
    created_at: datetime
    updated_at: datetime

    @classmethod
    def _base_fields(cls, model: Team) -> dict:
        return {
            "id": str(model.id),
            "track_id": str(model.track_id),
            "event_id": str(model.event_id),
            "owner": ParticipantDTO.from_model(model.owner),
            "required_roles": [RoleDTO.from_model(r) for r in model.required_roles],
            "name": model.name,
            "description": model.description,
            "status": model.status,
            "created_at": model.created_at,
            "updated_at": model.updated_at,
        }

    @classmethod
    def from_model(cls, model: Team) -> "TeamEventDTO":
        return cls(**cls._base_fields(model))


class TeamCreated(TeamEventDTO): ...


class TeamUpdated(TeamEventDTO): ...


class TeamDeleted(TeamEventDTO): ...


class TeamSubmitted(TeamEventDTO): ...


class MemberTeamEventDTO(TeamEventDTO):
    member: ParticipantDTO

    @classmethod
    def from_team_and_member(
        cls, team: Team, member: ParticipantModel
    ) -> "MemberTeamEventDTO":
        return cls(
            **cls._base_fields(team),
            member=ParticipantDTO.from_model(member),
        )


class MemberLeft(MemberTeamEventDTO): ...


class MemberKicked(MemberTeamEventDTO): ...
