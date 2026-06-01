import uuid
from datetime import datetime
from pydantic import BaseModel, Field

from src.models.team import Team, TeamStatusEnum
from src.models.track import Role
from src.models.event import Participant


class CreateTeamRequest(BaseModel):
    track_id: uuid.UUID
    event_id: uuid.UUID
    owner_id: uuid.UUID
    owner_role_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)

    def to_model(self, team_id: uuid.UUID) -> Team:
        owner = Participant(
            id=self.owner_id,
            event_id=self.event_id,
            name="",
            surname="",
            patronymic="",
            have_team=False,
            role_id=self.owner_role_id,
        )
        return Team(
            id=team_id,
            track_id=self.track_id,
            event_id=self.event_id,
            owner=owner,
            members=[],
            required_roles=[],
            name=self.name,
            description=self.description,
            status=TeamStatusEnum.BUILDING,
        )


class ChangeMemberRoleRequest(BaseModel):
    role_id: uuid.UUID


class UpdateTeamRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=500)
    status: TeamStatusEnum

    def to_model(self, team_id: uuid.UUID) -> Team:
        return Team(
            id=team_id,
            track_id=uuid.UUID(int=0),
            event_id=uuid.UUID(int=0),
            owner=Participant(
                id=uuid.UUID(int=0),
                event_id=uuid.UUID(int=0),
                name="",
                surname="",
                patronymic="",
                have_team=False,
            ),
            members=[],
            required_roles=[],
            name=self.name,
            description=self.description,
            status=self.status,
        )


class GetTeamResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    track_id: uuid.UUID
    event_id: uuid.UUID
    owner: Participant
    members: list[Participant]
    required_roles: list[Role]
    status: TeamStatusEnum
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, team: Team) -> "GetTeamResponse":
        return cls(
            id=team.id,
            name=team.name,
            description=team.description,
            track_id=team.track_id,
            event_id=team.event_id,
            owner=team.owner,
            members=team.members,
            required_roles=team.required_roles,
            status=team.status,
            created_at=team.created_at,
            updated_at=team.updated_at,
        )


class GetTeamsResponse(BaseModel):
    teams: list[GetTeamResponse]


class TeamSubmitResponse(BaseModel):
    team_id: uuid.UUID
    message: str = "Submission successful"
