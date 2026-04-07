"""
Protocols for Team Service
"""
from typing import Protocol, List, Optional
import uuid
from src.models.team import Team


class TeamRepository(Protocol):
    """Repository for team data access"""
    
    async def get_team(self, team_id: uuid.UUID) -> Team: ...
    
    async def create_team(self, team: Team) -> None: ...
    
    async def update_team(self, team: Team) -> None: ...
    
    async def delete_team(self, team_id: uuid.UUID) -> None: ...
    
    async def kick_member(self, team_id: uuid.UUID, user_id: uuid.UUID) -> None: ...
    
    async def team_submit(self, team_id: uuid.UUID, submission_url: str) -> None: ...
    
    async def update_member(self, team_id: uuid.UUID, user_id: uuid.UUID, role: str) -> None: ...
    
    async def change_team_status(self, team_id: uuid.UUID, status: str) -> None: ...
    
    async def add_member(self, team_id: uuid.UUID, user_id: uuid.UUID) -> None: ...


class UserRepository(Protocol):
    """Repository for user data access"""
    
    async def user_exists(self, user_id: uuid.UUID) -> bool: ...
    
    async def get_user(self, user_id: uuid.UUID) -> dict: ...


class EventClient(Protocol):
    """Client for Event Service"""
    
    async def event_exists(self, event_id: uuid.UUID) -> bool: ...
    
    async def get_event(self, event_id: uuid.UUID) -> dict: ...


class TrackClient(Protocol):
    """Client for Track Service"""
    
    async def track_exists(self, track_id: uuid.UUID) -> bool: ...
    
    async def get_track(self, track_id: uuid.UUID) -> dict: ...


class KafkaProducer(Protocol):
    """Kafka producer for team events"""
    
    async def send_team_created(self, team: Team) -> None: ...
    
    async def send_team_updated(self, team: Team) -> None: ...
    
    async def send_team_deleted(self, team_id: uuid.UUID) -> None: ...
    
    async def send_team_submitted(self, team_id: uuid.UUID, submission_url: str, event_id: uuid.UUID, track_id: uuid.UUID) -> None: ...
    
    async def send_member_left(self, team_id: uuid.UUID, user_id: uuid.UUID, event_id: uuid.UUID) -> None: ...
    
    async def send_member_kicked(self, team_id: uuid.UUID, user_id: uuid.UUID, kicked_by: uuid.UUID, event_id: uuid.UUID) -> None: ...
    
   