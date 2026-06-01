import uuid

import psycopg
import psycopg.rows
import psycopg_pool
from loguru import logger
from psycopg import Error
from psycopg.errors import UniqueViolation

from src.adapters.repository.tracing import trace_db_operation
import src.adapters.repository.errors as adapter_errors
from src.adapters.repository.errors import (
    InvitationNotFoundError,
    JoinRequestNotFoundError,
    ParticipantNotFoundError,
    RoleNotFoundError,
    TeamNotFoundError,
)
from src.adapters.repository.invitation.postgres.models import (
    InvitationRow,
    JoinRequestRow,
    ParticipantRow,
    RoleRow,
    TeamLookupRow,
)
from src.adapters.repository.invitation.postgres.queries import (
    CREATE_INVITATION_QUERY,
    CREATE_JOIN_REQUEST_QUERY,
    DECREMENT_TEAM_REQUIRED_COUNT_QUERY,
    DELETE_INVITATION_QUERY,
    DELETE_INVITATIONS_BY_MEMBER_QUERY,
    DELETE_JOIN_REQUEST_QUERY,
    DELETE_JOIN_REQUESTS_BY_MEMBER_QUERY,
    GET_INVITATION_QUERY,
    GET_INVITATIONS_BY_MEMBER_QUERY,
    GET_INVITATIONS_BY_TEAM_QUERY,
    GET_JOIN_REQUEST_QUERY,
    GET_JOIN_REQUESTS_BY_OWNER_QUERY,
    GET_JOIN_REQUESTS_BY_TEAM_QUERY,
    GET_JOIN_REQUESTS_BY_TRACK_AND_MEMBER_QUERY,
    GET_PARTICIPANT_QUERY,
    GET_ROLE_QUERY,
    GET_TEAM_FOR_INVITATION_QUERY,
    INSERT_TEAM_MEMBER_QUERY,
    SET_HAVE_TEAM_QUERY,
)
from src.models.event import Participant
from src.models.invitation import Invitation, JoinRequest
from src.models.track import Role


class InvitationPostgresRepository:
    def __init__(self, pool: psycopg_pool.AsyncConnectionPool) -> None:
        self._pool = pool

    @trace_db_operation("invitation_service", "INSERT", "invitation")
    async def create_invitation(self, invitation: Invitation) -> None:
        """Create a new invitation.

        Raises:
            TeamNotFoundError: team not found
            ParticipantNotFoundError: owner/member not found
            RoleNotFoundError: role not found
            InvitationAlreadyExistsError: duplicate invitation for (team_id, member_id)
        """
        logger.debug(
            "db_invitation_creation_started",
            invitation_id=str(invitation.id),
            team_id=str(invitation.team_id),
            member_id=str(invitation.member.id),
        )
        try:
            async with self._pool.connection() as conn:
                async with conn.transaction():
                    async with conn.cursor() as cursor:
                        try:
                            await cursor.execute(
                                CREATE_INVITATION_QUERY,
                                {
                                    "id": str(invitation.id),
                                    "team_id": str(invitation.team_id),
                                    "owner_id": str(invitation.owner.id),
                                    "member_id": str(invitation.member.id),
                                    "role_id": str(invitation.role.id),
                                    "description": invitation.description,
                                },
                            )
                        except UniqueViolation as e:
                            raise adapter_errors.InvitationAlreadyExistsError(
                                f"Invitation for team {invitation.team_id} "
                                f"and member {invitation.member.id} already exists"
                            ) from e
                        except psycopg.errors.ForeignKeyViolation as e:
                            raise self._translate_fk_violation(e) from e
        except (
            adapter_errors.InvitationAlreadyExistsError,
            adapter_errors.TeamNotFoundError,
            adapter_errors.ParticipantNotFoundError,
            adapter_errors.RoleNotFoundError,
        ):
            raise
        except Error as e:
            logger.error("db_invitation_repository_error", error=str(e))
            raise adapter_errors.RepositoryError from e

    @trace_db_operation("invitation_service", "SELECT", "invitation")
    async def get_invitation(self, invitation_id: uuid.UUID) -> Invitation:
        logger.debug("db_invitation_select_started", invitation_id=str(invitation_id))
        try:
            async with self._pool.connection() as conn:
                row = await self._fetch_invitation_row(conn, invitation_id)
                team = await self._get_team_lookup(conn, row.team_id)
                owner = await self._get_participant(conn, row.owner_id, team.event_id)
                member = await self._get_participant(conn, row.member_id, team.event_id)
                role = await self._get_role(conn, row.role_id)
                return row.to_model(owner=owner, member=member, role=role)
        except adapter_errors.InvitationNotFoundError:
            raise
        except Error as e:
            logger.error("db_invitation_repository_error", error=str(e))
            raise adapter_errors.RepositoryError from e

    @trace_db_operation("invitation_service", "SELECT", "invitation")
    async def get_invitations_by_team(self, team_id: uuid.UUID) -> list[Invitation]:
        logger.debug("db_invitations_by_team_select_started", team_id=str(team_id))
        try:
            async with self._pool.connection() as conn:
                team = await self._get_team_lookup(conn, team_id)
                return await self._load_invitations(
                    conn,
                    GET_INVITATIONS_BY_TEAM_QUERY,
                    {"team_id": str(team_id)},
                    event_id=team.event_id,
                )
        except adapter_errors.TeamNotFoundError:
            raise
        except Error as e:
            logger.error("db_invitation_repository_error", error=str(e))
            raise adapter_errors.RepositoryError from e

    @trace_db_operation("invitation_service", "SELECT", "invitation")
    async def get_invitations_by_member(self, member_id: uuid.UUID) -> list[Invitation]:
        logger.debug(
            "db_invitations_by_member_select_started", member_id=str(member_id)
        )
        try:
            async with self._pool.connection() as conn:
                return await self._load_invitations_multi_team(
                    conn,
                    GET_INVITATIONS_BY_MEMBER_QUERY,
                    {"member_id": str(member_id)},
                )
        except Error as e:
            logger.error("db_invitation_repository_error", error=str(e))
            raise adapter_errors.RepositoryError from e

    @trace_db_operation("invitation_service", "DELETE", "invitation")
    async def delete_invitation(self, invitation_id: uuid.UUID) -> None:
        logger.debug("db_invitation_deletion_started", invitation_id=str(invitation_id))
        try:
            async with self._pool.connection() as conn:
                async with conn.transaction():
                    async with conn.cursor() as cursor:
                        await cursor.execute(
                            DELETE_INVITATION_QUERY, {"id": str(invitation_id)}
                        )
                        if await cursor.fetchone() is None:
                            raise adapter_errors.InvitationNotFoundError(
                                f"Invitation {invitation_id} not found"
                            )
        except adapter_errors.InvitationNotFoundError:
            raise
        except Error as e:
            logger.error("db_invitation_repository_error", error=str(e))
            raise adapter_errors.RepositoryError from e

    @trace_db_operation("invitation_service", "UPDATE", "invitation")
    async def accept_invitation(self, invitation_id: uuid.UUID) -> Invitation:
        """Accept invitation: add member to team, decrement team roles,
        mark have_team, delete invitation. Also removes other pending
        invitations/join_requests for the same member.

        Raises:
            InvitationNotFoundError
            ParticipantAlreadyInTeamError
        """
        logger.debug("db_invitation_accept_started", invitation_id=str(invitation_id))
        try:
            async with self._pool.connection() as conn:
                async with conn.transaction():
                    row = await self._fetch_invitation_row(conn, invitation_id)
                    team = await self._get_team_lookup(conn, row.team_id)
                    owner = await self._get_participant(
                        conn, row.owner_id, team.event_id
                    )
                    member = await self._get_participant(
                        conn, row.member_id, team.event_id
                    )
                    role = await self._get_role(conn, row.role_id)

                    if member.have_team:
                        raise adapter_errors.ParticipantAlreadyInTeamError(
                            f"Participant {member.id} already in a team"
                        )

                    async with conn.cursor() as cursor:
                        await cursor.execute(
                            INSERT_TEAM_MEMBER_QUERY,
                            {
                                "team_id": str(row.team_id),
                                "member_id": str(row.member_id),
                                "role_id": str(row.role_id),
                            },
                        )
                        await cursor.execute(
                            DECREMENT_TEAM_REQUIRED_COUNT_QUERY,
                            {"team_id": str(row.team_id), "role_id": str(row.role_id)},
                        )
                        await cursor.execute(
                            SET_HAVE_TEAM_QUERY,
                            {
                                "participant_id": str(row.member_id),
                                "event_id": str(team.event_id),
                                "have_team": True,
                            },
                        )
                        # remove any other pending invitations/join requests
                        # for this member
                        # maybe delete this code later
                        await cursor.execute(
                            DELETE_INVITATIONS_BY_MEMBER_QUERY,
                            {"member_id": str(row.member_id)},
                        )
                        await cursor.execute(
                            DELETE_JOIN_REQUESTS_BY_MEMBER_QUERY,
                            {"member_id": str(row.member_id)},
                        )

                    # return refreshed state (member now have_team=True)
                    refreshed_member = Participant(
                        id=member.id,
                        event_id=member.event_id,
                        name=member.name,
                        surname=member.surname,
                        patronymic=member.patronymic,
                        have_team=True,
                        role_id=member.role_id,
                    )
                    return row.to_model(owner=owner, member=refreshed_member, role=role)
        except (
            adapter_errors.InvitationNotFoundError,
            adapter_errors.ParticipantAlreadyInTeamError,
        ):
            raise
        except Error as e:
            logger.error("db_invitation_repository_error", error=str(e))
            raise adapter_errors.RepositoryError from e

    @trace_db_operation("invitation_service", "INSERT", "join_request")
    async def create_join_request(self, join_request: JoinRequest) -> None:
        logger.debug(
            "db_join_request_creation_started",
            join_request_id=str(join_request.id),
            team_id=str(join_request.team_id),
            member_id=str(join_request.member.id),
        )
        try:
            async with self._pool.connection() as conn:
                async with conn.transaction():
                    async with conn.cursor() as cursor:
                        try:
                            await cursor.execute(
                                CREATE_JOIN_REQUEST_QUERY,
                                {
                                    "id": str(join_request.id),
                                    "team_id": str(join_request.team_id),
                                    "owner_id": str(join_request.owner.id),
                                    "member_id": str(join_request.member.id),
                                    "role_id": str(join_request.role.id),
                                    "description": join_request.description,
                                },
                            )
                        except UniqueViolation as e:
                            raise adapter_errors.JoinRequestAlreadyExistsError(
                                f"JoinRequest for team {join_request.team_id} "
                                f"and member {join_request.member.id} already exists"
                            ) from e
                        except psycopg.errors.ForeignKeyViolation as e:
                            raise self._translate_fk_violation(e) from e
        except (
            adapter_errors.JoinRequestAlreadyExistsError,
            adapter_errors.TeamNotFoundError,
            adapter_errors.ParticipantNotFoundError,
            adapter_errors.RoleNotFoundError,
        ):
            raise
        except Error as e:
            logger.error("db_invitation_repository_error", error=str(e))
            raise adapter_errors.RepositoryError from e

    @trace_db_operation("invitation_service", "SELECT", "join_request")
    async def get_join_request(self, join_request_id: uuid.UUID) -> JoinRequest:
        logger.debug(
            "db_join_request_select_started", join_request_id=str(join_request_id)
        )
        try:
            async with self._pool.connection() as conn:
                row = await self._fetch_join_request_row(conn, join_request_id)
                team = await self._get_team_lookup(conn, row.team_id)
                owner = await self._get_participant(conn, row.owner_id, team.event_id)
                member = await self._get_participant(conn, row.member_id, team.event_id)
                role = await self._get_role(conn, row.role_id)
                return row.to_model(owner=owner, member=member, role=role)
        except adapter_errors.JoinRequestNotFoundError:
            raise
        except Error as e:
            logger.error("db_invitation_repository_error", error=str(e))
            raise adapter_errors.RepositoryError from e

    @trace_db_operation("invitation_service", "SELECT", "join_request")
    async def get_join_requests_by_track_and_member(
        self, track_id: uuid.UUID, member_id: uuid.UUID
    ) -> list[JoinRequest]:
        logger.debug(
            "db_join_requests_by_track_member_select_started",
            track_id=str(track_id),
            member_id=str(member_id),
        )
        try:
            async with self._pool.connection() as conn:
                return await self._load_join_requests_multi_team(
                    conn,
                    GET_JOIN_REQUESTS_BY_TRACK_AND_MEMBER_QUERY,
                    {"track_id": str(track_id), "member_id": str(member_id)},
                )
        except Error as e:
            logger.error("db_invitation_repository_error", error=str(e))
            raise adapter_errors.RepositoryError from e

    @trace_db_operation("invitation_service", "SELECT", "join_request")
    async def get_join_requests_by_team(self, team_id: uuid.UUID) -> list[JoinRequest]:
        logger.debug("db_join_requests_by_team_select_started", team_id=str(team_id))
        try:
            async with self._pool.connection() as conn:
                team = await self._get_team_lookup(conn, team_id)
                return await self._load_join_requests(
                    conn,
                    GET_JOIN_REQUESTS_BY_TEAM_QUERY,
                    {"team_id": str(team_id)},
                    event_id=team.event_id,
                )
        except adapter_errors.TeamNotFoundError:
            raise
        except Error as e:
            logger.error("db_invitation_repository_error", error=str(e))
            raise adapter_errors.RepositoryError from e

    @trace_db_operation("invitation_service", "SELECT", "join_request")
    async def get_join_requests_by_owner(
        self, owner_id: uuid.UUID
    ) -> list[JoinRequest]:
        logger.debug("db_join_requests_by_owner_select_started", owner_id=str(owner_id))
        try:
            async with self._pool.connection() as conn:
                return await self._load_join_requests_multi_team(
                    conn,
                    GET_JOIN_REQUESTS_BY_OWNER_QUERY,
                    {"owner_id": str(owner_id)},
                )
        except Error as e:
            logger.error("db_invitation_repository_error", error=str(e))
            raise adapter_errors.RepositoryError from e

    @trace_db_operation("invitation_service", "DELETE", "join_request")
    async def delete_join_request(self, join_request_id: uuid.UUID) -> None:
        logger.debug(
            "db_join_request_deletion_started", join_request_id=str(join_request_id)
        )
        try:
            async with self._pool.connection() as conn:
                async with conn.transaction():
                    async with conn.cursor() as cursor:
                        await cursor.execute(
                            DELETE_JOIN_REQUEST_QUERY, {"id": str(join_request_id)}
                        )
                        if await cursor.fetchone() is None:
                            raise adapter_errors.JoinRequestNotFoundError(
                                f"JoinRequest {join_request_id} not found"
                            )
        except adapter_errors.JoinRequestNotFoundError:
            raise
        except Error as e:
            logger.error("db_invitation_repository_error", error=str(e))
            raise adapter_errors.RepositoryError from e

    @trace_db_operation("invitation_service", "UPDATE", "join_request")
    async def accept_join_request(self, join_request_id: uuid.UUID) -> JoinRequest:
        """Captain accepts join request: add member to team, decrement role,
        set have_team, delete all pending requests/invitations for member.
        """
        logger.debug(
            "db_join_request_accept_started", join_request_id=str(join_request_id)
        )
        try:
            async with self._pool.connection() as conn:
                async with conn.transaction():
                    row = await self._fetch_join_request_row(conn, join_request_id)
                    team = await self._get_team_lookup(conn, row.team_id)
                    owner = await self._get_participant(
                        conn, row.owner_id, team.event_id
                    )
                    member = await self._get_participant(
                        conn, row.member_id, team.event_id
                    )
                    role = await self._get_role(conn, row.role_id)

                    if member.have_team:
                        raise adapter_errors.ParticipantAlreadyInTeamError(
                            f"Participant {member.id} already in a team"
                        )

                    async with conn.cursor() as cursor:
                        await cursor.execute(
                            INSERT_TEAM_MEMBER_QUERY,
                            {
                                "team_id": str(row.team_id),
                                "member_id": str(row.member_id),
                                "role_id": str(row.role_id),
                            },
                        )
                        await cursor.execute(
                            DECREMENT_TEAM_REQUIRED_COUNT_QUERY,
                            {"team_id": str(row.team_id), "role_id": str(row.role_id)},
                        )
                        await cursor.execute(
                            SET_HAVE_TEAM_QUERY,
                            {
                                "participant_id": str(row.member_id),
                                "event_id": str(team.event_id),
                                "have_team": True,
                            },
                        )
                        await cursor.execute(
                            DELETE_INVITATIONS_BY_MEMBER_QUERY,
                            {"member_id": str(row.member_id)},
                        )
                        await cursor.execute(
                            DELETE_JOIN_REQUESTS_BY_MEMBER_QUERY,
                            {"member_id": str(row.member_id)},
                        )

                    refreshed_member = Participant(
                        id=member.id,
                        event_id=member.event_id,
                        name=member.name,
                        surname=member.surname,
                        patronymic=member.patronymic,
                        have_team=True,
                        role_id=member.role_id,
                    )
                    return row.to_model(owner=owner, member=refreshed_member, role=role)
        except (
            adapter_errors.JoinRequestNotFoundError,
            adapter_errors.ParticipantAlreadyInTeamError,
        ):
            raise
        except Error as e:
            logger.error("db_invitation_repository_error", error=str(e))
            raise adapter_errors.RepositoryError from e

    @staticmethod
    def _translate_fk_violation(e: psycopg.errors.ForeignKeyViolation) -> Exception:
        msg = str(e).lower()
        if "team" in msg:
            return TeamNotFoundError(f"Referenced team not found: {e}")
        if "role" in msg:
            return RoleNotFoundError(f"Referenced role not found: {e}")
        if "participant" in msg:
            return ParticipantNotFoundError(f"Referenced participant not found: {e}")
        return e

    async def _fetch_invitation_row(
        self, conn, invitation_id: uuid.UUID
    ) -> InvitationRow:
        async with conn.cursor(
            row_factory=psycopg.rows.class_row(InvitationRow)
        ) as cursor:
            await cursor.execute(GET_INVITATION_QUERY, {"id": str(invitation_id)})
            row = await cursor.fetchone()
            if row is None:
                raise InvitationNotFoundError(f"Invitation {invitation_id} not found")
            return row

    async def _fetch_join_request_row(
        self, conn, join_request_id: uuid.UUID
    ) -> JoinRequestRow:
        async with conn.cursor(
            row_factory=psycopg.rows.class_row(JoinRequestRow)
        ) as cursor:
            await cursor.execute(GET_JOIN_REQUEST_QUERY, {"id": str(join_request_id)})
            row = await cursor.fetchone()
            if row is None:
                raise JoinRequestNotFoundError(
                    f"JoinRequest {join_request_id} not found"
                )
            return row

    async def _get_team_lookup(self, conn, team_id: uuid.UUID) -> TeamLookupRow:
        async with conn.cursor(
            row_factory=psycopg.rows.class_row(TeamLookupRow)
        ) as cursor:
            await cursor.execute(GET_TEAM_FOR_INVITATION_QUERY, {"id": str(team_id)})
            row = await cursor.fetchone()
            if row is None:
                raise TeamNotFoundError(f"Team {team_id} not found")
            return row

    async def _get_team_lookup_or_raise(
        self, conn, team_id: uuid.UUID
    ) -> TeamLookupRow:
        return await self._get_team_lookup(conn, team_id)

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
            if row is None:
                raise ParticipantNotFoundError(
                    f"Participant {participant_id} not found for event {event_id}"
                )
            return row.to_model()

    async def _get_role(self, conn, role_id: uuid.UUID) -> Role:
        async with conn.cursor(row_factory=psycopg.rows.class_row(RoleRow)) as cursor:
            await cursor.execute(GET_ROLE_QUERY, {"id": str(role_id)})
            row = await cursor.fetchone()
            if row is None:
                raise RoleNotFoundError(f"Role {role_id} not found")
            return row.to_model()

    async def _load_invitations(
        self, conn, query: str, params: dict, event_id: uuid.UUID
    ) -> list[Invitation]:
        async with conn.cursor(
            row_factory=psycopg.rows.class_row(InvitationRow)
        ) as cursor:
            await cursor.execute(query, params)
            rows = await cursor.fetchall()

        result: list[Invitation] = []
        for row in rows:
            owner = await self._get_participant(conn, row.owner_id, event_id)
            member = await self._get_participant(conn, row.member_id, event_id)
            role = await self._get_role(conn, row.role_id)
            result.append(row.to_model(owner=owner, member=member, role=role))
        return result

    async def _load_invitations_multi_team(
        self, conn, query: str, params: dict
    ) -> list[Invitation]:
        async with conn.cursor(
            row_factory=psycopg.rows.class_row(InvitationRow)
        ) as cursor:
            await cursor.execute(query, params)
            rows = await cursor.fetchall()

        result: list[Invitation] = []
        for row in rows:
            team = await self._get_team_lookup(conn, row.team_id)
            owner = await self._get_participant(conn, row.owner_id, team.event_id)
            member = await self._get_participant(conn, row.member_id, team.event_id)
            role = await self._get_role(conn, row.role_id)
            result.append(row.to_model(owner=owner, member=member, role=role))
        return result

    async def _load_join_requests(
        self, conn, query: str, params: dict, event_id: uuid.UUID
    ) -> list[JoinRequest]:
        async with conn.cursor(
            row_factory=psycopg.rows.class_row(JoinRequestRow)
        ) as cursor:
            await cursor.execute(query, params)
            rows = await cursor.fetchall()

        result: list[JoinRequest] = []
        for row in rows:
            owner = await self._get_participant(conn, row.owner_id, event_id)
            member = await self._get_participant(conn, row.member_id, event_id)
            role = await self._get_role(conn, row.role_id)
            result.append(row.to_model(owner=owner, member=member, role=role))
        return result

    async def _load_join_requests_multi_team(
        self, conn, query: str, params: dict
    ) -> list[JoinRequest]:
        async with conn.cursor(
            row_factory=psycopg.rows.class_row(JoinRequestRow)
        ) as cursor:
            await cursor.execute(query, params)
            rows = await cursor.fetchall()

        result: list[JoinRequest] = []
        for row in rows:
            team = await self._get_team_lookup(conn, row.team_id)
            owner = await self._get_participant(conn, row.owner_id, team.event_id)
            member = await self._get_participant(conn, row.member_id, team.event_id)
            role = await self._get_role(conn, row.role_id)
            result.append(row.to_model(owner=owner, member=member, role=role))
        return result
