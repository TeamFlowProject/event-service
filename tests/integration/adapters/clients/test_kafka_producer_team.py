import uuid
from datetime import datetime
from typing import cast

import pytest
from uuid_extensions import uuid7
from aiokafka import AIOKafkaConsumer

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
from tests.integration.adapters.clients.test_kafka_producer import _consume_one


def _make_participant(event_id: uuid.UUID) -> Participant:
    return Participant(
        id=cast(uuid.UUID, uuid7()),
        event_id=event_id,
        name="John",
        surname="Doe",
        patronymic="Smith",
        have_team=False,
    )


def _make_team() -> Team:
    event_id = cast(uuid.UUID, uuid7())
    owner = _make_participant(event_id)
    return Team(
        id=cast(uuid.UUID, uuid7()),
        track_id=cast(uuid.UUID, uuid7()),
        event_id=event_id,
        owner=owner,
        members=[owner],
        required_roles=[],
        name="Test Team",
        description="A test team",
        status=TeamStatusEnum.DRAFT,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def _assert_team_message(message: dict, team: Team) -> None:
    assert message["id"] == str(team.id)
    assert message["track_id"] == str(team.track_id)
    assert message["event_id"] == str(team.event_id)
    assert message["name"] == team.name
    assert message["description"] == team.description
    assert message["status"] == team.status.value
    assert message["owner"]["id"] == str(team.owner.id)
    assert len(message["members"]) == len(team.members)


def _assert_member_event(message: dict, team: Team, member: Participant) -> None:
    assert message["team_id"] == str(team.id)
    assert message["event_id"] == str(team.event_id)
    assert message["track_id"] == str(team.track_id)
    assert message["member"]["id"] == str(member.id)


@pytest.mark.integration
class TestKafkaProducerClientTeam:
    @pytest.mark.asyncio
    async def test_send_team_created(self, kafka_producer_client, kafka_container):
        team = _make_team()

        await kafka_producer_client.send_team_created(team)

        message = await _consume_one(kafka_container, TEAM_CREATED)
        _assert_team_message(message, team)

    @pytest.mark.asyncio
    async def test_send_team_updated(self, kafka_producer_client, kafka_container):
        team = _make_team()
        team.name = "Updated Team"

        await kafka_producer_client.send_team_updated(team)

        message = await _consume_one(kafka_container, TEAM_UPDATED)
        _assert_team_message(message, team)

    @pytest.mark.asyncio
    async def test_send_team_deleted(self, kafka_producer_client, kafka_container):
        team = _make_team()

        await kafka_producer_client.send_team_deleted(team)

        message = await _consume_one(kafka_container, TEAM_DELETED)
        _assert_team_message(message, team)

    @pytest.mark.asyncio
    async def test_send_team_submitted(self, kafka_producer_client, kafka_container):
        team = _make_team()
        team.status = TeamStatusEnum.SUBMITTED

        await kafka_producer_client.send_team_submitted(team)

        message = await _consume_one(kafka_container, TEAM_SUBMITTED)
        _assert_team_message(message, team)

    @pytest.mark.asyncio
    async def test_send_member_left(self, kafka_producer_client, kafka_container):
        team = _make_team()
        member = _make_participant(team.event_id)

        await kafka_producer_client.send_member_left(team, member)

        message = await _consume_one(kafka_container, TEAM_MEMBER_LEFT)
        _assert_member_event(message, team, member)

    @pytest.mark.asyncio
    async def test_send_member_kicked(self, kafka_producer_client, kafka_container):
        team = _make_team()
        member = _make_participant(team.event_id)

        await kafka_producer_client.send_member_kicked(team, member)

        message = await _consume_one(kafka_container, TEAM_MEMBER_KICKED)
        _assert_member_event(message, team, member)
