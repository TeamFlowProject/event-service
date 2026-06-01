import uuid

import psycopg
import psycopg.rows
import psycopg_pool
from loguru import logger
from psycopg import Error
from psycopg.errors import UniqueViolation

from src.adapters.repository.tracing import trace_db_operation
import src.adapters.repository.errors as adapter_errors
from src.adapters.repository.team.postgres.models import (
    TeamRow,
    TeamRoleRow,
    RoleRow,
    ParticipantRow,
)
from src.adapters.repository.errors import (
    TeamNotFoundError,
    ParticipantNotFoundError,
)
from src.adapters.repository.team.postgres.queries import (
    CREATE_TEAM_QUERY,
    GET_TEAM_QUERY,
    GET_TEAM_QUERY_BY_EVENT_ID,
    GET_TEAM_QUERY_BY_USER_ID,
    GET_USER_TEAM_IN_EVENT,
    UPDATE_TEAM_QUERY,
    DELETE_TEAM_QUERY,
    CHANGE_TEAM_STATUS_QUERY,
    REMOVE_TEAM_MEMBER_QUERY,
    GET_TEAM_MEMBERS_QUERY,
    INSERT_TEAM_ROLE_QUERY,
    GET_TEAM_ROLES_QUERY,
    DECREMENT_REQUIRED_COUNT_QUERY,
    INCREMENT_REQUIRED_COUNT_QUERY,
    GET_ROLES_BY_TRACK_QUERY,
    GET_PARTICIPANT_QUERY,
    SET_HAVE_TEAM_QUERY,
    RESET_TEAM_MEMBERS_HAVE_TEAM_QUERY,
    CHANGE_OWNER_ROLE_QUERY,
    CHANGE_MEMBER_ROLE_QUERY,
    GET_MEMBER_ROLE_IN_TEAM_QUERY,
)
from src.models.team import Team, TeamStatusEnum
from src.models.event import Participant
from src.models.track import Role


class TeamPostgresRepository:
    def __init__(self, pool: psycopg_pool.AsyncConnectionPool) -> None:
        self._pool = pool

    @trace_db_operation("team_service", "SELECT", "team")
    async def get_team(self, team_id: uuid.UUID) -> Team:
        logger.debug("db_team_select_started", team_id=str(team_id))
        try:
            async with self._pool.connection() as conn:
                async with conn.cursor(
                    row_factory=psycopg.rows.class_row(TeamRow)
                ) as cursor:
                    await cursor.execute(GET_TEAM_QUERY, {"id": str(team_id)})
                    row = await cursor.fetchone()
                    if not row:
                        raise TeamNotFoundError(f"Team {team_id} not found")

                owner = await self._get_participant(conn, row.owner_id, row.event_id)
                members = await self._get_team_members(conn, row.id, row.event_id)
                required_roles = await self._get_team_roles(conn, row.id)

                return row.to_model(owner, members, required_roles)
        except TeamNotFoundError:
            raise
        except Error as e:
            logger.error("db_team_repository_error", error=str(e))
            raise adapter_errors.RepositoryError from e

    @trace_db_operation("team_service", "SELECT", "participants")
    async def get_member_by_id(
        self, member_id: uuid.UUID, event_id: uuid.UUID
    ) -> Participant:
        logger.debug(
            "db_member_select_started",
            member_id=str(member_id),
            event_id=str(event_id),
        )
        try:
            async with self._pool.connection() as conn:
                async with conn.cursor(
                    row_factory=psycopg.rows.class_row(ParticipantRow)
                ) as cursor:
                    await cursor.execute(
                        GET_PARTICIPANT_QUERY,
                        {"id": str(member_id), "event_id": str(event_id)},
                    )
                    row = await cursor.fetchone()
                    if not row:
                        raise ParticipantNotFoundError(
                            f"Participant {member_id} not found"
                        )
                    return row.to_model()
        except ParticipantNotFoundError:
            raise
        except Error as e:
            logger.error("db_team_repository_error", error=str(e))
            raise adapter_errors.RepositoryError from e

    @trace_db_operation("team_service", "INSERT", "team")
    async def create_team(self, team: Team) -> None:
        logger.debug(
            "db_team_creation_started",
            team_id=str(team.id),
            event_id=str(team.event_id),
        )
        try:
            async with self._pool.connection() as conn:
                async with conn.transaction():
                    async with conn.cursor() as cursor:
                        try:
                            await cursor.execute(
                                CREATE_TEAM_QUERY,
                                {
                                    "id": str(team.id),
                                    "track_id": str(team.track_id),
                                    "event_id": str(team.event_id),
                                    "owner_id": str(team.owner.id),
                                    "owner_role_id": (
                                        str(team.owner.role_id)
                                        if team.owner.role_id is not None
                                        else None
                                    ),
                                    "name": team.name,
                                    "description": team.description,
                                    "status": team.status.value,
                                    "created_at": team.created_at,
                                    "updated_at": team.updated_at,
                                },
                            )
                        except UniqueViolation as e:
                            raise adapter_errors.TeamAlreadyExistsError(
                                f"Team {team.id} already exists"
                            ) from e

                        # Fetch roles for this track and populate team_roles
                        track_roles = await self._get_roles_by_track(
                            conn, team.track_id
                        )
                        for role in track_roles:
                            await cursor.execute(
                                INSERT_TEAM_ROLE_QUERY,
                                {
                                    "team_id": str(team.id),
                                    "role_id": str(role.id),
                                    "required_count": role.count,
                                },
                            )

                        # Account for owner role slot only
                        if team.owner.role_id is not None:
                            await cursor.execute(
                                DECREMENT_REQUIRED_COUNT_QUERY,
                                {
                                    "team_id": str(team.id),
                                    "role_id": str(team.owner.role_id),
                                },
                            )

                        await cursor.execute(
                            SET_HAVE_TEAM_QUERY,
                            {
                                "participant_id": str(team.owner.id),
                                "event_id": str(team.event_id),
                                "have_team": True,
                            },
                        )
        except adapter_errors.TeamAlreadyExistsError:
            raise
        except Error as e:
            logger.error("db_team_repository_error", error=str(e))
            raise adapter_errors.RepositoryError from e

    @trace_db_operation("team_service", "UPDATE", "team")
    async def update_team(self, team: Team) -> None:
        logger.debug("db_team_update_started", team_id=str(team.id))
        try:
            async with self._pool.connection() as conn:
                async with conn.transaction():
                    async with conn.cursor() as cursor:
                        await cursor.execute(
                            UPDATE_TEAM_QUERY,
                            {
                                "id": str(team.id),
                                "name": team.name,
                                "description": team.description,
                                "status": team.status.value,
                            },
                        )
                        result = await cursor.fetchone()
                        if not result:
                            raise adapter_errors.TeamNotFoundError(
                                f"Team {team.id} not found"
                            )
        except adapter_errors.TeamNotFoundError:
            raise
        except Error as e:
            logger.error("db_team_repository_error", error=str(e))
            raise adapter_errors.RepositoryError from e

    @trace_db_operation("team_service", "DELETE", "team")
    async def delete_team(self, team_id: uuid.UUID) -> None:
        logger.debug("db_team_deletion_started", team_id=str(team_id))
        try:
            async with self._pool.connection() as conn:
                async with conn.transaction():
                    async with conn.cursor(
                        row_factory=psycopg.rows.class_row(TeamRow)
                    ) as cursor:
                        await cursor.execute(GET_TEAM_QUERY, {"id": str(team_id)})
                        row = await cursor.fetchone()
                        if not row:
                            raise adapter_errors.TeamNotFoundError(
                                f"Team {team_id} not found"
                            )

                    async with conn.cursor() as cursor:
                        # Reset have_team for all members in team_members
                        await cursor.execute(
                            RESET_TEAM_MEMBERS_HAVE_TEAM_QUERY,
                            {"team_id": str(team_id), "event_id": str(row.event_id)},
                        )
                        # Reset have_team for owner
                        await cursor.execute(
                            SET_HAVE_TEAM_QUERY,
                            {
                                "participant_id": str(row.owner_id),
                                "event_id": str(row.event_id),
                                "have_team": False,
                            },
                        )
                        await cursor.execute(DELETE_TEAM_QUERY, {"id": str(team_id)})
        except adapter_errors.TeamNotFoundError:
            raise
        except Error as e:
            logger.error("db_team_repository_error", error=str(e))
            raise adapter_errors.RepositoryError from e

    @trace_db_operation("team_service", "UPDATE", "team")
    async def change_team_status(
        self, team_id: uuid.UUID, status: TeamStatusEnum
    ) -> None:
        logger.debug(
            "db_team_status_change_started", team_id=str(team_id), status=status.value
        )
        try:
            async with self._pool.connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        CHANGE_TEAM_STATUS_QUERY,
                        {"id": str(team_id), "status": status.value},
                    )
                    result = await cursor.fetchone()
                    if not result:
                        raise adapter_errors.TeamNotFoundError(
                            f"Team {team_id} not found"
                        )
        except adapter_errors.TeamNotFoundError:
            raise
        except Error as e:
            logger.error("db_team_repository_error", error=str(e))
            raise adapter_errors.RepositoryError from e

    @trace_db_operation("team_service", "DELETE", "team_members")
    async def remove_member(self, team_id: uuid.UUID, member_id: uuid.UUID) -> None:
        logger.debug(
            "db_member_removal_started",
            team_id=str(team_id),
            member_id=str(member_id),
        )
        try:
            async with self._pool.connection() as conn:
                async with conn.transaction():
                    async with conn.cursor(
                        row_factory=psycopg.rows.class_row(TeamRow)
                    ) as cursor:
                        await cursor.execute(GET_TEAM_QUERY, {"id": str(team_id)})
                        team_row = await cursor.fetchone()
                        if not team_row:
                            raise adapter_errors.TeamNotFoundError(
                                f"Team {team_id} not found"
                            )

                    async with conn.cursor() as cursor:
                        await cursor.execute(
                            REMOVE_TEAM_MEMBER_QUERY,
                            {"team_id": str(team_id), "member_id": str(member_id)},
                        )
                        result = await cursor.fetchone()
                        if not result:
                            raise adapter_errors.TeamNotFoundError(
                                f"Member {member_id} not found in team {team_id}"
                            )
                        role_id = result[1]

                        await cursor.execute(
                            INCREMENT_REQUIRED_COUNT_QUERY,
                            {"team_id": str(team_id), "role_id": str(role_id)},
                        )
                        await cursor.execute(
                            SET_HAVE_TEAM_QUERY,
                            {
                                "participant_id": str(member_id),
                                "event_id": str(team_row.event_id),
                                "have_team": False,
                            },
                        )
        except adapter_errors.TeamNotFoundError:
            raise
        except Error as e:
            logger.error("db_team_repository_error", error=str(e))
            raise adapter_errors.RepositoryError from e

    @trace_db_operation("team_service", "UPDATE", "team_members")
    async def change_member_role(
        self,
        team_id: uuid.UUID,
        member_id: uuid.UUID,
        new_role_id: uuid.UUID,
    ) -> uuid.UUID:
        """
        Меняет роль участника команды (или владельца).
        Возвращает старый role_id для рассылки событий.
        """
        logger.debug(
            "db_change_member_role_started",
            team_id=str(team_id),
            member_id=str(member_id),
            new_role_id=str(new_role_id),
        )
        try:
            async with self._pool.connection() as conn:
                async with conn.transaction():
                    async with conn.cursor() as cursor:
                        await cursor.execute(GET_TEAM_QUERY, {"id": str(team_id)})
                        team_row = await cursor.fetchone()
                        if not team_row:
                            raise adapter_errors.TeamNotFoundError(
                                f"Team {team_id} not found"
                            )
                        owner_id = team_row[3]
                        is_owner = str(owner_id) == str(member_id)

                        if is_owner:
                            old_role_id = team_row[4]
                            if old_role_id is None:
                                raise adapter_errors.RepositoryError(
                                    "Owner has no role assigned"
                                )
                            await cursor.execute(
                                CHANGE_OWNER_ROLE_QUERY,
                                {
                                    "team_id": str(team_id),
                                    "role_id": str(new_role_id),
                                },
                            )
                            if not await cursor.fetchone():
                                raise adapter_errors.TeamNotFoundError(
                                    f"Team {team_id} not found"
                                )
                        else:
                            await cursor.execute(
                                GET_MEMBER_ROLE_IN_TEAM_QUERY,
                                {
                                    "team_id": str(team_id),
                                    "member_id": str(member_id),
                                },
                            )
                            row = await cursor.fetchone()
                            if not row:
                                raise adapter_errors.ParticipantNotFoundError(
                                    f"Member {member_id} not in team {team_id}"
                                )
                            old_role_id = row[0]
                            await cursor.execute(
                                CHANGE_MEMBER_ROLE_QUERY,
                                {
                                    "team_id": str(team_id),
                                    "member_id": str(member_id),
                                    "role_id": str(new_role_id),
                                },
                            )
                            if not await cursor.fetchone():
                                raise adapter_errors.ParticipantNotFoundError(
                                    f"Member {member_id} not in team {team_id}"
                                )

                        await cursor.execute(
                            INCREMENT_REQUIRED_COUNT_QUERY,
                            {"team_id": str(team_id), "role_id": str(old_role_id)},
                        )
                        await cursor.execute(
                            DECREMENT_REQUIRED_COUNT_QUERY,
                            {"team_id": str(team_id), "role_id": str(new_role_id)},
                        )
                        return old_role_id
        except (
            adapter_errors.TeamNotFoundError,
            adapter_errors.ParticipantNotFoundError,
        ):
            raise
        except Error as e:
            logger.error("db_team_repository_error", error=str(e))
            raise adapter_errors.RepositoryError from e

    async def _get_participant(
        self, conn, participant_id: uuid.UUID, event_id: uuid.UUID
    ) -> Participant:
        async with conn.cursor(
            row_factory=psycopg.rows.class_row(ParticipantRow)
        ) as cursor:
            await cursor.execute(
                GET_PARTICIPANT_QUERY,
                {"id": str(participant_id), "event_id": str(event_id)},
            )
            row = await cursor.fetchone()
            if not row:
                raise ParticipantNotFoundError(
                    f"Participant {participant_id} not found"
                )
            return row.to_model()

    async def _get_team_members(
        self, conn, team_id: uuid.UUID, event_id: uuid.UUID
    ) -> list[Participant]:
        async with conn.cursor(
            row_factory=psycopg.rows.class_row(ParticipantRow)
        ) as cursor:
            await cursor.execute(
                GET_TEAM_MEMBERS_QUERY,
                {"team_id": str(team_id), "event_id": str(event_id)},
            )
            rows = await cursor.fetchall()
            return [row.to_model() for row in rows]

    async def _get_team_roles(self, conn, team_id: uuid.UUID) -> list[Role]:
        async with conn.cursor(
            row_factory=psycopg.rows.class_row(TeamRoleRow)
        ) as cursor:
            await cursor.execute(GET_TEAM_ROLES_QUERY, {"team_id": str(team_id)})
            rows = await cursor.fetchall()
            return [row.to_model() for row in rows]

    async def _get_roles_by_track(self, conn, track_id: uuid.UUID) -> list[Role]:
        async with conn.cursor(row_factory=psycopg.rows.class_row(RoleRow)) as cursor:
            await cursor.execute(GET_ROLES_BY_TRACK_QUERY, {"track_id": str(track_id)})
            rows = await cursor.fetchall()
            return [row.to_model() for row in rows]

    @trace_db_operation("team_service", "SELECT", "team")
    async def get_teams_by_event_id(self, event_id: uuid.UUID) -> list[Team]:
        logger.debug("db_teams_by_event_select_started", event_id=str(event_id))
        try:
            async with self._pool.connection() as conn:
                async with conn.cursor(
                    row_factory=psycopg.rows.class_row(TeamRow)
                ) as cursor:
                    await cursor.execute(
                        GET_TEAM_QUERY_BY_EVENT_ID, {"event_id": str(event_id)}
                    )
                    rows = await cursor.fetchall()
                    teams = []
                    for row in rows:
                        owner = await self._get_participant(
                            conn, row.owner_id, row.event_id
                        )
                        members = await self._get_team_members(
                            conn, row.id, row.event_id
                        )
                        required_roles = await self._get_team_roles(conn, row.id)
                        teams.append(row.to_model(owner, members, required_roles))

                    return teams
        except Error as e:
            logger.error("db_team_repository_error", error=str(e))
            raise adapter_errors.RepositoryError from e

    @trace_db_operation("team_service", "SELECT", "team")
    async def get_teams_by_user_id(self, user_id: uuid.UUID) -> list[Team]:
        logger.debug("db_teams_by_user_select_started", user_id=str(user_id))
        try:
            async with self._pool.connection() as conn:
                async with conn.cursor(
                    row_factory=psycopg.rows.class_row(TeamRow)
                ) as cursor:
                    await cursor.execute(
                        GET_TEAM_QUERY_BY_USER_ID, {"user_id": str(user_id)}
                    )
                    rows = await cursor.fetchall()
                    teams = []
                    for row in rows:
                        owner = await self._get_participant(
                            conn, row.owner_id, row.event_id
                        )
                        members = await self._get_team_members(
                            conn, row.id, row.event_id
                        )
                        required_roles = await self._get_team_roles(conn, row.id)
                        teams.append(row.to_model(owner, members, required_roles))

                    return teams
        except Error as e:
            logger.error("db_team_repository_error", error=str(e))
            raise adapter_errors.RepositoryError from e

    @trace_db_operation("team_service", "SELECT", "team")
    async def get_user_team_in_event(
        self, user_id: uuid.UUID, event_id: uuid.UUID
    ) -> Team | None:
        logger.debug(
            "db_user_team_in_event_select_started",
            user_id=str(user_id),
            event_id=str(event_id),
        )
        try:
            async with self._pool.connection() as conn:
                async with conn.cursor(
                    row_factory=psycopg.rows.class_row(TeamRow)
                ) as cursor:
                    await cursor.execute(
                        GET_USER_TEAM_IN_EVENT,
                        {"event_id": str(event_id), "user_id": str(user_id)},
                    )
                    row = await cursor.fetchone()

                    if not row:
                        return None

                    owner = await self._get_participant(
                        conn, row.owner_id, row.event_id
                    )
                    members = await self._get_team_members(conn, row.id, row.event_id)
                    required_roles = await self._get_team_roles(conn, row.id)
                    return row.to_model(owner, members, required_roles)
        except Error as e:
            logger.error("db_team_repository_error", error=str(e))
            raise adapter_errors.RepositoryError from e
