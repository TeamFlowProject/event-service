from typing import Optional

from pydantic import BaseModel

from src.models.event import Participant as ParticipantModel
from src.models.invitation import Invitation, JoinRequest
from src.models.track import Role as RoleModel


class Role(BaseModel):
    id: str
    track_id: str
    name: str
    description: str
    count: int

    @classmethod
    def from_model(cls, model: RoleModel) -> "Role":
        return cls(
            id=str(model.id),
            track_id=str(model.track_id),
            name=model.name,
            description=model.description,
            count=model.count,
        )


class Participant(BaseModel):
    id: str
    event_id: str
    name: str
    surname: str
    patronymic: str
    have_team: bool
    role_id: Optional[str] = None

    @classmethod
    def from_model(cls, model: ParticipantModel) -> "Participant":
        return cls(
            id=str(model.id),
            event_id=str(model.event_id),
            name=model.name,
            surname=model.surname,
            patronymic=model.patronymic,
            have_team=model.have_team,
            role_id=str(model.role_id) if model.role_id else None,
        )


class InvitationDTO(BaseModel):
    id: str
    team_id: str
    owner: Participant
    member: Participant
    role: Role
    description: str

    @classmethod
    def from_model(cls, model: Invitation) -> "InvitationDTO":
        return cls(
            id=str(model.id),
            team_id=str(model.team_id),
            owner=Participant.from_model(model.owner),
            member=Participant.from_model(model.member),
            role=Role.from_model(model.role),
            description=model.description,
        )


class JoinRequestDTO(BaseModel):
    id: str
    team_id: str
    owner: Participant
    member: Participant
    role: Role
    description: str

    @classmethod
    def from_model(cls, model: JoinRequest) -> "JoinRequestDTO":
        return cls(
            id=str(model.id),
            team_id=str(model.team_id),
            owner=Participant.from_model(model.owner),
            member=Participant.from_model(model.member),
            role=Role.from_model(model.role),
            description=model.description,
        )


class InvitationCreated(InvitationDTO): ...


class InvitationCanceled(InvitationDTO): ...


class InvitationAccepted(InvitationDTO): ...


class InvitationRejected(InvitationDTO): ...


class JoinRequestCreated(JoinRequestDTO): ...


class JoinRequestCanceled(JoinRequestDTO): ...


class JoinRequestAccepted(JoinRequestDTO): ...


class JoinRequestRejected(JoinRequestDTO): ...
