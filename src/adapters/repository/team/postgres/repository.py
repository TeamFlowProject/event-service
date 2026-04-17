from datetime import datetime, timezone
from typing import Optional
import uuid
import psycopg
import psycopg.rows
import psycopg_pool
import json
from dataclasses import asdict

from src.adapters.repository.team.postgres.models import TeamRow
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
    UPDATE_TEAM_STATUS_QUERY,
    ADD_TEAM_MEMBER_QUERY,
    REMOVE_TEAM_MEMBER_QUERY,
    GET_TEAM_MEMBERS_QUERY,
    CHECK_MEMBER_IN_TEAM_QUERY,
    GET_MEMBER_TEAM_QUERY,
    GET_PARTICIPANT_WITH_TEAM_STATUS_QUERY,
    GET_TEAMS_BY_EVENT_QUERY,
    GET_TEAMS_BY_OWNER_QUERY,
    COUNT_TEAMS_BY_EVENT_QUERY,
)
from src.models.team import Team, TeamStatusEnum
from src.models.event import Participant
from src.models.track import Role


class TeamPostgresRepository:
    def __init__(self, pool: psycopg_pool.AsyncConnectionPool) -> None:
        self._pool = pool

    async def create_team(self, team: Team) -> None:
        async with self._pool.connection() as conn:
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
                            "required_roles": json.dumps(
                                [asdict(role) for role in team.required_roles]
                            ),
                            "status": team.status.value,
                            "created_at": team.created_at,
                            "updated_at": team.updated_at,
                        },
                    )
                except psycopg.errors.UniqueViolation as e:
                    raise TeamAlreadyExistsError(
                        f"Team {team.id} already exists"
                    ) from e

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

                return row.to_model(owner, members)

    async def update_team(
        self,
        team_id: uuid.UUID,
        name: str,
        description: str,
        required_roles: list[Role],
        status: TeamStatusEnum,
    ) -> None:
        async with self._pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    UPDATE_TEAM_QUERY,
                    {
                        "id": str(team_id),
                        "name": name,
                        "description": description,
                        "required_roles": json.dumps(
                            [asdict(role) for role in required_roles]
                        ),
                        "status": status.value,
                    },
                )
                result = await cursor.fetchone()
                if not result:
                    raise TeamNotFoundError(f"Team {team_id} not found")

    async def delete_team(self, team_id: uuid.UUID) -> None:
        async with self._pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(DELETE_TEAM_QUERY, {"id": str(team_id)})
                result = await cursor.fetchone()
                if not result:
                    raise TeamNotFoundError(f"Team {team_id} not found")

    async def update_team_status(
        self, team_id: uuid.UUID, status: TeamStatusEnum
    ) -> None:
        async with self._pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    UPDATE_TEAM_STATUS_QUERY,
                    {"id": str(team_id), "status": status.value},
                )
                result = await cursor.fetchone()
                if not result:
                    raise TeamNotFoundError(f"Team {team_id} not found")

    async def get_teams_by_event(
        self, event_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> tuple[list[Team], int]:
        async with self._pool.connection() as conn:
            async with conn.cursor(
                row_factory=psycopg.rows.class_row(TeamRow)
            ) as cursor:
                await cursor.execute(
                    GET_TEAMS_BY_EVENT_QUERY,
                    {"event_id": str(event_id), "limit": limit, "offset": offset},
                )
                rows = await cursor.fetchall()

                teams = []
                for row in rows:
                    owner = await self._get_participant(
                        conn, row.owner_id, row.event_id
                    )
                    members = await self._get_team_members(conn, row.id, row.event_id)
                    teams.append(row.to_model(owner, members))

                async with conn.cursor() as count_cursor:
                    await count_cursor.execute(
                        COUNT_TEAMS_BY_EVENT_QUERY, {"event_id": str(event_id)}
                    )
                    count_result = await count_cursor.fetchone()
                    total_count = count_result[0] if count_result else 0

            return teams, total_count

    async def get_teams_by_owner(self, owner_id: uuid.UUID) -> list[Team]:
        async with self._pool.connection() as conn:
            async with conn.cursor(
                row_factory=psycopg.rows.class_row(TeamRow)
            ) as cursor:
                await cursor.execute(
                    GET_TEAMS_BY_OWNER_QUERY, {"owner_id": str(owner_id)}
                )
                rows = await cursor.fetchall()

                teams = []
                for row in rows:
                    owner = await self._get_participant(
                        conn, row.owner_id, row.event_id
                    )
                    members = await self._get_team_members(conn, row.id, row.event_id)
                    teams.append(row.to_model(owner, members))
                return teams

    async def add_member(self, team_id: uuid.UUID, member_id: uuid.UUID) -> None:
        async with self._pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    ADD_TEAM_MEMBER_QUERY,
                    {
                        "team_id": str(team_id),
                        "member_id": str(member_id),
                        "joined_at": datetime.now(timezone.utc),
                    },
                )

    async def remove_member(self, team_id: uuid.UUID, member_id: uuid.UUID) -> None:
        async with self._pool.connection() as conn:
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

    async def is_member_in_team(self, team_id: uuid.UUID, member_id: uuid.UUID) -> bool:
        async with self._pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    CHECK_MEMBER_IN_TEAM_QUERY,
                    {"team_id": str(team_id), "member_id": str(member_id)},
                )
                result = await cursor.fetchone()
                return result[0] if result else False

    async def get_member_team(self, member_id: uuid.UUID) -> Optional[uuid.UUID]:
        async with self._pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    GET_MEMBER_TEAM_QUERY, {"member_id": str(member_id)}
                )
                result = await cursor.fetchone()
                return uuid.UUID(result[0]) if result else None

    async def update_team_with_members(
        self,
        team_id: uuid.UUID,
        name: str,
        description: str,
        required_roles: list[Role],
        status: TeamStatusEnum,
        members: list[uuid.UUID],
    ) -> None:
        async with self._pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor() as cursor:
                    # Обновляем команду
                    await cursor.execute(
                        UPDATE_TEAM_QUERY,
                        {
                            "id": str(team_id),
                            "name": name,
                            "description": description,
                            "required_roles": json.dumps(
                                [asdict(role) for role in required_roles]
                            ),
                            "status": status.value,
                        },
                    )
                    result = await cursor.fetchone()
                    if not result:
                        raise TeamNotFoundError(f"Team {team_id} not found")

                    # Удаляем всех текущих членов команды
                    await cursor.execute(
                        "DELETE FROM team_members WHERE team_id = %s", (str(team_id),)
                    )

                    # Добавляем новых членов
                    for member_id in members:
                        await cursor.execute(
                            ADD_TEAM_MEMBER_QUERY,
                            {
                                "team_id": str(team_id),
                                "member_id": str(member_id),
                                "joined_at": datetime.now(timezone.utc),
                            },
                        )

    async def create_team_with_members(
        self, team: Team, member_ids: list[uuid.UUID]
    ) -> None:
        async with self._pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor() as cursor:
                    # Создаем команду
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
                                "required_roles": json.dumps(
                                    [asdict(role) for role in team.required_roles]
                                ),
                                "status": team.status.value,
                                "created_at": team.created_at,
                                "updated_at": team.updated_at,
                            },
                        )
                    except psycopg.errors.UniqueViolation as e:
                        raise TeamAlreadyExistsError(
                            f"Team {team.id} already exists"
                        ) from e

                    # Добавляем участников (включая владельца)
                    all_member_ids = list(set(member_ids + [team.owner.id]))
                    for member_id in all_member_ids:
                        await cursor.execute(
                            ADD_TEAM_MEMBER_QUERY,
                            {
                                "team_id": str(team.id),
                                "member_id": str(member_id),
                                "joined_at": datetime.now(timezone.utc),
                            },
                        )

    async def _get_participant(
        self, conn, participant_id: uuid.UUID, event_id: uuid.UUID
    ) -> Participant:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cursor:
            await cursor.execute(
                GET_PARTICIPANT_WITH_TEAM_STATUS_QUERY, {"id": str(participant_id)}
            )
            row = await cursor.fetchone()

            if not row:
                raise ParticipantNotFoundError(
                    f"Participant {participant_id} not found"
                )

            return Participant(
                id=uuid.UUID(row["id"]) if isinstance(row["id"], str) else row["id"],
                event_id=event_id,
                name=row["name"],
                surname=row["surname"],
                patronymic=row["patronymic"],
                have_team=row["have_team"],
            )

    async def _get_team_members(
        self, conn, team_id: uuid.UUID, event_id: uuid.UUID
    ) -> list[Participant]:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cursor:
            await cursor.execute(GET_TEAM_MEMBERS_QUERY, {"team_id": str(team_id)})
            rows = await cursor.fetchall()

            members = []
            for row in rows:
                member = await self._get_participant(conn, row["member_id"], event_id)
                members.append(member)
            return members
