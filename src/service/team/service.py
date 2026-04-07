from src.service.team.protocols import TeamRepository, UserRepository, EventClient, TrackClient, KafkaProducer
from src.models.team import Team, TeamStatusEnum
import uuid
from datetime import datetime
from typing import Optional
import src.adapters.repository.errors as adapter_errors
import src.service.errors as service_errors


class TeamService:
    def __init__(
        self,
        team_repository: TeamRepository,
        user_repository: UserRepository,
        event_client: EventClient,
        track_client: TrackClient,
        kafka_producer: KafkaProducer,
    ) -> None:
        self._team_repository = team_repository
        self._user_repository = user_repository
        self._event_client = event_client
        self._track_client = track_client
        self._kafka_producer = kafka_producer

    async def get_teams(self, team_id: uuid.UUID) -> Team:
        """
        Get a team by ID

        Args:
            team_id (uuid.UUID): The ID of the team to get

        Returns:
            Team: The team with the given ID

        Raises:
            TeamNotFoundError: If the team could not be found
        """
        try:
            return await self._team_repository.get_team(team_id)
        except adapter_errors.TeamNotFoundError as e:
            raise service_errors.TeamNotFoundError("Failed to get team") from e


    async def create_team(self, request: CreateTeamRequestDTO) -> uuid.UUID:
        """
        Create a new team

        Args:
            request (CreateTeamRequestDTO): The team data to create

        Returns:
            uuid.UUID: The ID of the created team

        Raises:
            EventNotFoundError: If the event does not exist
            TrackNotFoundError: If the track does not exist
            UserNotFoundError: If the owner does not exist
            TeamAlreadyExistsError: If user already has a team in this track
        """
        # Check if event exists
        try:
            if not await self._event_client.event_exists(request.event_id):
                raise service_errors.EventNotFoundError(f"Event {request.event_id} does not exist")
        except adapter_errors.EventNotFoundError as e:
            raise service_errors.EventNotFoundError("Failed to create team") from e

        # Check if track exists
        try:
            if not await self._track_client.track_exists(request.track_id):
                raise service_errors.TrackNotFoundError(f"Track {request.track_id} does not exist")
        except adapter_errors.TrackNotFoundError as e:
            raise service_errors.TrackNotFoundError("Failed to create team") from e

        # Check if user exists
        try:
            if not await self._user_repository.user_exists(request.owner_id):
                raise service_errors.UserNotFoundError(f"User {request.owner_id} does not exist")
        except adapter_errors.UserNotFoundError as e:
            raise service_errors.UserNotFoundError("Failed to create team") from e

        # Check if user already has a team in this track
        try:
            user_teams = await self._team_repository.get_teams_by_user(request.owner_id)
            for team in user_teams:
                if team.track_id == request.track_id:
                    raise service_errors.TeamAlreadyExistsError(
                        f"User {request.owner_id} already has a team in track {request.track_id}"
                    )
        except adapter_errors.TeamAlreadyExistsError as e:
            raise service_errors.TeamAlreadyExistsError("Failed to create team") from e

        # Create team
        now = datetime.now()
        team = Team(
            id=uuid.uuid4(),
            name=request.name,
            description=request.description,
            track_id=request.track_id,
            event_id=request.event_id,
            owner_id=request.owner_id,
            member_ids=[request.owner_id],
            required_roles=request.required_roles,
            status=TeamStatusEnum.DRAFT,
            created_at=now,
            updated_at=now
        )

        try:
            await self._team_repository.create_team(team)
            await self._kafka_producer.send_team_created(team)
        except adapter_errors.TeamNotFoundError as e:
            raise service_errors.TeamNotFoundError("Failed to create team") from e

        return team.id

    async def update_team(self, team_id: uuid.UUID, request: UpdateTeamRequestDTO) -> None:
        """
        Update an existing team

        Updates full state of the team including all roles and members

        Args:
            team_id (uuid.UUID): The ID of the team to update
            request (UpdateTeamRequestDTO): The team data to update

        Raises:
            TeamNotFoundError: If the team could not be updated
        """
        try:
            team = await self._team_repository.get_team(team_id)
            
            if request.name is not None:
                team.name = request.name
            if request.description is not None:
                team.description = request.description
            if request.required_roles is not None:
                team.required_roles = request.required_roles
            
            team.updated_at = datetime.now()
            
            await self._team_repository.update_team(team)
            await self._kafka_producer.send_team_updated(team)
        except adapter_errors.TeamNotFoundError as e:
            raise service_errors.TeamNotFoundError("Failed to update team") from e

    async def delete_team(self, team_id: uuid.UUID) -> None:
        """
        Delete an existing team

        Args:
            team_id (uuid.UUID): The ID of the team to delete

        Raises:
            TeamNotFoundError: If the team could not be deleted
        """
        try:
            await self._team_repository.delete_team(team_id)
            await self._kafka_producer.send_team_deleted(team_id)
        except adapter_errors.TeamNotFoundError as e:
            raise service_errors.TeamNotFoundError("Failed to delete team") from e

    async def leave_team(self, team_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """
        User leaves a team

        Args:
            team_id (uuid.UUID): The ID of the team to leave
            user_id (uuid.UUID): The ID of the user leaving

        Raises:
            TeamNotFoundError: If the team could not be found
            UserNotFoundError: If the user is not a member
            TeamOperationError: If owner tries to leave
        """
        try:
            team = await self._team_repository.get_team(team_id)
            
            if user_id not in team.member_ids:
                raise service_errors.UserNotFoundError(f"User {user_id} is not a member of team {team_id}")
            
            if team.owner_id == user_id:
                raise service_errors.TeamOperationError("Team owner cannot leave. Use delete_team instead.")
            
            await self._team_repository.kick_member(team_id, user_id)
            await self._kafka_producer.send_member_left(team_id, user_id, team.event_id)
        except adapter_errors.TeamNotFoundError as e:
            raise service_errors.TeamNotFoundError("Failed to leave team") from e

    async def kick_member(self, team_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """
        Kick a member from a team

        Args:
            team_id (uuid.UUID): The ID of the team
            user_id (uuid.UUID): The ID of the user to kick

        Raises:
            TeamNotFoundError: If the team could not be found
            UserNotFoundError: If the user is not a member
            TeamOperationError: If trying to kick the owner
        """
        try:
            team = await self._team_repository.get_team(team_id)
            
            if user_id not in team.member_ids:
                raise service_errors.UserNotFoundError(f"User {user_id} is not a member of team {team_id}")
            
            if team.owner_id == user_id:
                raise service_errors.TeamOperationError("Cannot kick team owner")
            
            await self._team_repository.kick_member(team_id, user_id)
            await self._kafka_producer.send_member_kicked(team_id, user_id, team.owner_id, team.event_id)
        except adapter_errors.TeamNotFoundError as e:
            raise service_errors.TeamNotFoundError("Failed to kick member") from e

    async def team_submit(self, team_id: uuid.UUID, submission_url: str) -> None:
        """
        Submit a team for review

        Args:
            team_id (uuid.UUID): The ID of the team to submit
            submission_url (str): The URL of the team's work

        Raises:
            TeamNotFoundError: If the team could not be found
            TeamOperationError: If the team is not in FULL status
        """
        try:
            team = await self._team_repository.get_team(team_id)
            
            if team.status != TeamStatusEnum.FULL:
                raise service_errors.TeamOperationError(
                    f"Cannot submit team in {team.status.value} status. Team must be {TeamStatusEnum.FULL.value}."
                )
            
            await self._team_repository.team_submit(team_id, submission_url)
            await self._kafka_producer.send_team_submitted(team_id, submission_url, team.event_id, team.track_id)
        except adapter_errors.TeamNotFoundError as e:
            raise service_errors.TeamNotFoundError("Failed to submit team") from e

    async def update_member(self, team_id: uuid.UUID, user_id: uuid.UUID, role: str) -> None:
        """
        Update a member's role in a team

        Args:
            team_id (uuid.UUID): The ID of the team
            user_id (uuid.UUID): The ID of the user
            role (str): The new role for the user

        Raises:
            TeamNotFoundError: If the team could not be found
            UserNotFoundError: If the user is not a member
            TeamOperationError: If trying to update the owner's role
        """
        try:
            team = await self._team_repository.get_team(team_id)
            
            if user_id not in team.member_ids:
                raise service_errors.UserNotFoundError(f"User {user_id} is not a member of team {team_id}")
            
            if team.owner_id == user_id:
                raise service_errors.TeamOperationError("Cannot update owner's role via update_member")
            
            await self._team_repository.update_member(team_id, user_id, role)
            await self._kafka_producer.send_member_updated(team_id, user_id, role, team.event_id)
        except adapter_errors.TeamNotFoundError as e:
            raise service_errors.TeamNotFoundError("Failed to update member") from e

    async def change_team_status(self, team_id: uuid.UUID, status: TeamStatusEnum) -> None:
        """
        Change a team's status

        Args:
            team_id (uuid.UUID): The ID of the team
            status (TeamStatusEnum): The new status for the team

        Raises:
            TeamNotFoundError: If the team could not be found
        """
        try:
            team = await self._team_repository.get_team(team_id)
            old_status = team.status
            
            await self._team_repository.change_team_status(team_id, status.value)
            await self._kafka_producer.send_team_status_changed(team_id, old_status.value, status.value, team.event_id)
        except adapter_errors.TeamNotFoundError as e:
            raise service_errors.TeamNotFoundError("Failed to change team status") from e

    async def add_member(self, team_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """
        Add a member to a team

        Args:
            team_id (uuid.UUID): The ID of the team
            user_id (uuid.UUID): The ID of the user to add

        Raises:
            TeamNotFoundError: If the team could not be found
            UserNotFoundError: If the user does not exist or is already a member
            TeamAlreadyExistsError: If user already has a team in this track
        """
        try:
            team = await self._team_repository.get_team(team_id)
            
            # Check if user exists
            if not await self._user_repository.user_exists(user_id):
                raise service_errors.UserNotFoundError(f"User {user_id} does not exist")
            
            # Check if user is already a member
            if user_id in team.member_ids:
                raise service_errors.UserNotFoundError(f"User {user_id} is already a member of team {team_id}")
            
            # Check if user already has a team in this track
            user_teams = await self._team_repository.get_teams_by_user(user_id)
            for ut in user_teams:
                if ut.track_id == team.track_id:
                    raise service_errors.TeamAlreadyExistsError(
                        f"User {user_id} already has a team in track {team.track_id}"
                    )
            
            await self._team_repository.add_member(team_id, user_id)
            await self._kafka_producer.send_member_added(team_id, user_id, team.event_id, team.track_id)
        except adapter_errors.TeamNotFoundError as e:
            raise service_errors.TeamNotFoundError("Failed to add member") from e