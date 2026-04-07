from typing import Protocol
import uuid
from src.models.team import Team


class TeamRepository(Protocol):
    """Repository for team data access"""

    async def get_team(self, team_id: uuid.UUID) -> Team: ...

    async def remove_member(self, team_id: uuid.UUID, user_id: uuid.UUID) -> None: ...

    async def delete_team(self, team_id: uuid.UUID) -> None: ...

    async def create_team(self, team: Team) -> None: ...

    async def update_team(self, team: Team) -> None: ...

    async def change_team_status(self, team_id: uuid.UUID, status: str) -> None: ...


class KafkaProducer(Protocol):
    """Kafka producer for team events"""

    async def send_team_created(self, team: Team) -> None: ...

    async def send_team_updated(self, team: Team) -> None: ...

    async def send_team_deleted(self, team_id: uuid.UUID) -> None: ...

    async def send_team_submitted(
        self,
        team_id: uuid.UUID,
        submission_url: str,
        event_id: uuid.UUID,
        track_id: uuid.UUID,
    ) -> None: ...

    async def send_member_left(
        self, team_id: uuid.UUID, user_id: uuid.UUID, event_id: uuid.UUID
    ) -> None: ...

    async def send_member_kicked(
        self,
        team_id: uuid.UUID,
        user_id: uuid.UUID,
        kicked_by: uuid.UUID,
        event_id: uuid.UUID,
    ) -> None: ...
