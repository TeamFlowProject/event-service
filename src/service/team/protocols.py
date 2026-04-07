"""
Protocols for Team Service
"""
from typing import Protocol, List, Optional
import uuid
from src.models.team import Team


class TeamRepository(Protocol):
    """Repository for team data access"""
    
    async def get_team(self, team_id: uuid.UUID) -> Team:
        """Get a team by ID"""
        ...
    
    async def get_teams_by_event(self, event_id: uuid.UUID) -> List[Team]:
        """Get all teams for an event"""
        ...
    
    async def get_teams_by_user(self, user_id: uuid.UUID) -> List[Team]:
        """Get all teams where user is a member"""
        ...
    
    async def get_teams_by_owner(self, owner_id: uuid.UUID) -> List[Team]:
        """Get all teams where user is owner"""
        ...
    
    async def create_team(self, team: Team) -> None:
        """Create a new team"""
        ...
    
    async def update_team(self, team: Team) -> None:
        """Update an existing team"""
        ...
    
    async def delete_team(self, team_id: uuid.UUID) -> None:
        """Delete a team"""
        ...
    
    async def kick_member(self, team_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Remove a member from a team"""
        ...
    
    async def team_submit(self, team_id: uuid.UUID, submission_url: str) -> None:
        """Submit a team for review"""
        ...
    
    async def update_member(self, team_id: uuid.UUID, user_id: uuid.UUID, role: str) -> None:
        """Update a member's role"""
        ...
    
    async def change_team_status(self, team_id: uuid.UUID, status: str) -> None:
        """Change team status"""
        ...
    
    async def add_member(self, team_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Add a member to a team"""
        ...


class UserRepository(Protocol):
    """Repository for user data access"""
    
    async def user_exists(self, user_id: uuid.UUID) -> bool:
        """Check if user exists"""
        ...
    
    async def get_user(self, user_id: uuid.UUID) -> dict:
        """Get user by ID"""
        ...


class EventClient(Protocol):
    """Client for Event Service"""
    
    async def event_exists(self, event_id: uuid.UUID) -> bool:
        """Check if event exists"""
        ...
    
    async def get_event(self, event_id: uuid.UUID) -> dict:
        """Get event by ID"""
        ...


class TrackClient(Protocol):
    """Client for Track Service"""
    
    async def track_exists(self, track_id: uuid.UUID) -> bool:
        """Check if track exists"""
        ...
    
    async def get_track(self, track_id: uuid.UUID) -> dict:
        """Get track by ID"""
        ...


class KafkaProducer(Protocol):
    """Kafka producer for team events"""
    
    async def send_team_created(self, team: Team) -> None:
        """Send team created event"""
        ...
    
    async def send_team_updated(self, team: Team) -> None:
        """Send team updated event"""
        ...
    
    async def send_team_deleted(self, team_id: uuid.UUID) -> None:
        """Send team deleted event"""
        ...
    
    async def send_team_submitted(self, team_id: uuid.UUID, submission_url: str, event_id: uuid.UUID, track_id: uuid.UUID) -> None:
        """Send team submitted event"""
        ...
    
    async def send_team_status_changed(self, team_id: uuid.UUID, old_status: str, new_status: str, event_id: uuid.UUID) -> None:
        """Send team status changed event"""
        ...
    
    async def send_member_added(self, team_id: uuid.UUID, user_id: uuid.UUID, event_id: uuid.UUID, track_id: uuid.UUID) -> None:
        """Send member added event"""
        ...
    
    async def send_member_removed(self, team_id: uuid.UUID, user_id: uuid.UUID, event_id: uuid.UUID) -> None:
        """Send member removed event"""
        ...
    
    async def send_member_left(self, team_id: uuid.UUID, user_id: uuid.UUID, event_id: uuid.UUID) -> None:
        """Send member left event"""
        ...
    
    async def send_member_kicked(self, team_id: uuid.UUID, user_id: uuid.UUID, kicked_by: uuid.UUID, event_id: uuid.UUID) -> None:
        """Send member kicked event"""
        ...
    
    async def send_member_updated(self, team_id: uuid.UUID, user_id: uuid.UUID, role: str, event_id: uuid.UUID) -> None:
        """Send member updated event"""
        ...