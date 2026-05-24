import uuid
from datetime import datetime
from typing import cast

import pytest
from uuid_extensions import uuid7

from src.adapters.clients.topics import (
    TEAM_CREATED,
    TEAM_UPDATED,
    TEAM_DELETED,
    TEAM_SUBMITTED,
    TEAM_MEMBER_LEFT,
    TEAM_MEMBER_KICKED,
)
from src.models.team import Team, TeamStatusEnum
from src.models.event import Participant
from src.models.track import Role
from tests.integration.adapters.clients.test_kafka_producer import _consume_one


def _make_participant(
    event_id: uuid.UUID, *, role_id: uuid.UUID | None = None
) -> Participant:
    return Participant(
        id=cast(uuid.UUID, uuid7()),
        event_id=event_id,
        name="John",
        surname="Doe",
        patronymic="Smith",
        have_team=False,
        role_id=role_id,
    )


def _make_team() -> Team:
    event_id = cast(uuid.UUID, uuid7())
    track_id = cast(uuid.UUID, uuid7())
    owner = _make_participant(event_id)
    return Team(
        id=cast(uuid.UUID, uuid7()),
        track_id=track_id,
        event_id=event_id,
        owner=owner,
        members=[owner],
        required_roles=[
            Role(
                id=cast(uuid.UUID, uuid7()),
                track_id=track_id,
                name="Developer",
                description="Backend developer",
                count=2,
            ),
        ],
        name="Test Team",
        description="A test team",
        status=TeamStatusEnum.DRAFT,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def _assert_participant_dto(message: dict, participant: Participant) -> None:
    assert message["id"] == str(participant.id)
    assert message["name"] == participant.name
    assert message["surname"] == participant.surname
    assert message["patronymic"] == participant.patronymic
    if participant.role_id is not None:
        assert message["role_id"] == str(participant.role_id)
    else:
        assert message.get("role_id") is None
    assert "event_id" not in message
    assert "have_team" not in message


def _assert_role_dto(message: dict, role: Role) -> None:
    assert message["id"] == str(role.id)
    assert message["track_id"] == str(role.track_id)
    assert message["name"] == role.name
    assert message["description"] == role.description
    assert message["count"] == role.count


def _assert_team_event(message: dict, team: Team) -> None:
    assert message["id"] == str(team.id)
    assert message["track_id"] == str(team.track_id)
    assert message["event_id"] == str(team.event_id)
    assert message["name"] == team.name
    assert message["description"] == team.description
    assert message["status"] == team.status.value
    _assert_participant_dto(message["owner"], team.owner)
    assert len(message["required_roles"]) == len(team.required_roles)
    for msg_role, model_role in zip(message["required_roles"], team.required_roles):
        _assert_role_dto(msg_role, model_role)
    assert "owner_id" not in message
    assert "member_ids" not in message
    assert "members" not in message


def _assert_member_team_event(message: dict, team: Team, member: Participant) -> None:
    _assert_team_event(message, team)
    _assert_participant_dto(message["member"], member)
    assert "member_id" not in message
    assert "team_id" not in message


@pytest.mark.integration
class TestKafkaProducerClientTeam:
    @pytest.mark.asyncio
    async def test_send_team_created(self, kafka_producer_client, kafka_container):
        team = _make_team()

        await kafka_producer_client.send_team_created(team)

        message = await _consume_one(kafka_container, TEAM_CREATED)
        _assert_team_event(message, team)

    @pytest.mark.asyncio
    async def test_send_team_updated(self, kafka_producer_client, kafka_container):
        team = _make_team()
        team.name = "Updated Team"

        await kafka_producer_client.send_team_updated(team)

        message = await _consume_one(kafka_container, TEAM_UPDATED)
        _assert_team_event(message, team)

    @pytest.mark.asyncio
    async def test_send_team_deleted(self, kafka_producer_client, kafka_container):
        team = _make_team()

        await kafka_producer_client.send_team_deleted(team)

        message = await _consume_one(kafka_container, TEAM_DELETED)
        _assert_team_event(message, team)

    @pytest.mark.asyncio
    async def test_send_team_submitted(self, kafka_producer_client, kafka_container):
        team = _make_team()
        team.status = TeamStatusEnum.SUBMITTED

        await kafka_producer_client.send_team_submitted(team)

        message = await _consume_one(kafka_container, TEAM_SUBMITTED)
        _assert_team_event(message, team)

    @pytest.mark.asyncio
    async def test_send_member_left(self, kafka_producer_client, kafka_container):
        team = _make_team()
        member = _make_participant(
            team.event_id,
            role_id=cast(uuid.UUID, uuid7()),
        )

        await kafka_producer_client.send_member_left(team, member)

        message = await _consume_one(kafka_container, TEAM_MEMBER_LEFT)
        _assert_member_team_event(message, team, member)

    @pytest.mark.asyncio
    async def test_send_member_kicked(self, kafka_producer_client, kafka_container):
        team = _make_team()
        member = _make_participant(
            team.event_id,
            role_id=cast(uuid.UUID, uuid7()),
        )

        await kafka_producer_client.send_member_kicked(team, member)

        message = await _consume_one(kafka_container, TEAM_MEMBER_KICKED)
        _assert_member_team_event(message, team, member)
