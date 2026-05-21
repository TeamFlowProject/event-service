from datetime import datetime

from pydantic import BaseModel

from src.adapters.clients.dto.invitation import Participant, Role
from src.models.event import Participant as ParticipantModel
from src.models.team import Team, TeamStatusEnum


class TeamDTO(BaseModel):
    id: str
    track_id: str
    event_id: str
    owner: Participant
    members: list[Participant]
    required_roles: list[Role]
    name: str
    description: str
    status: TeamStatusEnum
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, model: Team) -> "TeamDTO":
        return cls(
            id=str(model.id),
            track_id=str(model.track_id),
            event_id=str(model.event_id),
            owner=Participant.from_model(model.owner),
            members=[Participant.from_model(m) for m in model.members],
            required_roles=[Role.from_model(r) for r in model.required_roles],
            name=model.name,
            description=model.description,
            status=model.status,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class TeamCreated(TeamDTO): ...


class TeamUpdated(TeamDTO): ...


class TeamDeleted(TeamDTO): ...


class TeamSubmitted(TeamDTO): ...


class MemberEventDTO(BaseModel):
    team_id: str
    event_id: str
    track_id: str
    member: Participant

    @classmethod
    def from_model(cls, team: Team, member: ParticipantModel) -> "MemberEventDTO":
        return cls(
            team_id=str(team.id),
            event_id=str(team.event_id),
            track_id=str(team.track_id),
            member=Participant.from_model(member),
        )


class MemberLeft(MemberEventDTO): ...


class MemberKicked(MemberEventDTO): ...
