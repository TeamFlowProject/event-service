import uuid
from typing import Protocol

from src.models.team import TeamStatusEnum


class TeamService(Protocol):
    async def change_team_status(
        self, team_id: uuid.UUID, status: TeamStatusEnum
    ) -> None: ...
