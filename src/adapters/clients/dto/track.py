from pydantic import BaseModel
from datetime import datetime
from src.models.track import Track, Role as RoleModel, TrackStatusEnum


class Role(BaseModel):
    id: str
    name: str
    description: str
    count: int

    @classmethod
    def from_model(cls, model: RoleModel) -> "Role":
        return cls(
            id=str(model.id),
            name=model.name,
            description=model.description,
            count=model.count,
        )


class TrackDTO(BaseModel):
    id: str
    event_id: str
    name: str
    description: str
    max_team_count: int
    max_participants_count: int
    min_team_size: int
    max_team_size: int
    required_roles: list[Role]
    requirements: str
    status: TrackStatusEnum
    registration_deadline: datetime

    @classmethod
    def from_model(cls, model: Track) -> "TrackDTO":
        return cls(
            id=str(model.id),
            event_id=str(model.event_id),
            name=model.name,
            description=model.description,
            max_team_count=model.max_team_count,
            max_participants_count=model.max_participants_count,
            min_team_size=model.min_team_size,
            max_team_size=model.max_team_size,
            required_roles=[Role.from_model(role) for role in model.required_roles],
            requirements=model.requirements,
            status=model.status,
            registration_deadline=model.registration_deadline,
        )


class TrackCreated(TrackDTO): ...


class TrackUpdated(TrackDTO): ...


class TrackDeleted(TrackDTO): ...
