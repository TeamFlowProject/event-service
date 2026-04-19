import uuid

import psycopg
import psycopg.rows
import psycopg_pool

from src.adapters.repository.team.postgres.models import (
    TeamRow,
    TeamRoleRow,
    RoleRow,
    ParticipantRow,
)
from src.adapters.repository.errors import (
    TeamNotFoundError,
    ParticipantNotFoundError,
    TeamAlreadyExistsError,
)
from src.adapters.repository.team.postgres.queries import (
    CREATE_TEAM_QUERY,
    GET_TEAM_QUERY,
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
)
from src.models.team import Team, TeamStatusEnum
from src.models.event import Participant
from src.models.track import Role


class TeamPostgresRepository:
    def __init__(self, pool: psycopg_pool.AsyncConnectionPool) -> None:
        self._pool = pool

    async def get_team(self, team_id: uuid.UUID) -> Team:
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

    async def get_member_by_id(
        self, member_id: uuid.UUID, event_id: uuid.UUID
    ) -> Participant:
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
                    raise ParticipantNotFoundError(f"Participant {member_id} not found")
                return row.to_model()

    async def create_team(self, team: Team) -> None:
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
                                "name": team.name,
                                "description": team.description,
                                "status": team.status.value,
                                "created_at": team.created_at,
                                "updated_at": team.updated_at,
                            },
                        )
                    except psycopg.errors.UniqueViolation as e:
                        raise TeamAlreadyExistsError(
                            f"Team {team.id} already exists"
                        ) from e

                    # Fetch roles for this track and populate team_roles
                    track_roles = await self._get_roles_by_track(conn, team.track_id)
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

    async def update_team(self, team: Team) -> None:
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
                        raise TeamNotFoundError(f"Team {team.id} not found")

    async def delete_team(self, team_id: uuid.UUID) -> None:
        async with self._pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor(
                    row_factory=psycopg.rows.class_row(TeamRow)
                ) as cursor:
                    await cursor.execute(GET_TEAM_QUERY, {"id": str(team_id)})
                    row = await cursor.fetchone()
                    if not row:
                        raise TeamNotFoundError(f"Team {team_id} not found")

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

    async def change_team_status(
        self, team_id: uuid.UUID, status: TeamStatusEnum
    ) -> None:
        async with self._pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    CHANGE_TEAM_STATUS_QUERY,
                    {"id": str(team_id), "status": status.value},
                )
                result = await cursor.fetchone()
                if not result:
                    raise TeamNotFoundError(f"Team {team_id} not found")

    async def remove_member(self, team_id: uuid.UUID, member_id: uuid.UUID) -> None:
        async with self._pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor(
                    row_factory=psycopg.rows.class_row(TeamRow)
                ) as cursor:
                    await cursor.execute(GET_TEAM_QUERY, {"id": str(team_id)})
                    team_row = await cursor.fetchone()
                    if not team_row:
                        raise TeamNotFoundError(f"Team {team_id} not found")

                async with conn.cursor() as cursor:
                    await cursor.execute(
                        REMOVE_TEAM_MEMBER_QUERY,
                        {"team_id": str(team_id), "member_id": str(member_id)},
                    )
                    result = await cursor.fetchone()
                    if not result:
                        raise TeamNotFoundError(
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

    async def get_all_teams(self) -> list[Team]:
        async with self._pool.connection() as conn:
            async with conn.cursor(
                row_factory=psycopg.rows.class_row(TeamRow)
            ) as cursor:
                await cursor.execute("SELECT * FROM teams")
                rows = await cursor.fetchall()

                teams = []
                for row in rows:
                    owner = await self._get_participant(
                        conn, row.owner_id, row.event_id
                    )
                    members = await self._get_team_members(conn, row.id, row.event_id)
                    required_roles = await self._get_team_roles(conn, row.id)
                    teams.append(row.to_model(owner, members, required_roles))

                return teams
