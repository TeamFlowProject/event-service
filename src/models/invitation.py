import uuid
from dataclasses import dataclass

from src.models.event import Participant
from src.models.track import Role


@dataclass
class Invitation:
    id: uuid.UUID
    team_id: uuid.UUID
    owner: Participant
    member: Participant
    role: Role
    description: str = ""


@dataclass
class JoinRequest:
    id: uuid.UUID
    team_id: uuid.UUID
    owner: Participant
    member: Participant
    role: Role
    description: str = ""
