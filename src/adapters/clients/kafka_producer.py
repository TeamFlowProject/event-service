from aiokafka import AIOKafkaProducer
import uuid

from src.models import Event
from src.models.track import Track
from pydantic import BaseModel
from src.adapters.clients.topics import (
    TRACK_CREATED,
    TRACK_UPDATED,
    TRACK_DELETED,
    INVITATION_CREATED,
    INVITATION_CANCELED,
    INVITATION_ACCEPTED,
    INVITATION_REJECTED,
    JOIN_REQUEST_CREATED,
    JOIN_REQUEST_CANCELED,
    JOIN_REQUEST_ACCEPTED,
    JOIN_REQUEST_REJECTED,
)
from src.adapters.clients.dto.track import TrackCreated, TrackUpdated, TrackDeleted
from src.adapters.clients.dto.invitation import (
    InvitationCreated,
    InvitationCanceled,
    InvitationAccepted,
    InvitationRejected,
    JoinRequestCreated,
    JoinRequestCanceled,
    JoinRequestAccepted,
    JoinRequestRejected,
)
from src.models.invitation import Invitation, JoinRequest


def dto_serializer(dto: BaseModel) -> bytes:
    return dto.model_dump_json().encode("utf-8")


class KafkaProducerClient:
    def __init__(self, producer: AIOKafkaProducer) -> None:
        self._producer = producer

    async def send_create_track(self, track: Track) -> None:
        await self._producer.send_and_wait(
            topic=TRACK_CREATED,
            value=TrackCreated.from_model(track),
        )

    async def send_update_track(self, track: Track) -> None:
        await self._producer.send_and_wait(
            topic=TRACK_UPDATED,
            value=TrackUpdated.from_model(track),
        )

    async def send_delete_track(self, track: Track) -> None:
        await self._producer.send_and_wait(
            topic=TRACK_DELETED,
            value=TrackDeleted.from_model(track),
        )

    async def send_create_event(self, event: Event) -> None: ...

    async def send_update_event(self, event: Event) -> None: ...

    async def send_delete_event(self, event_id: uuid.UUID) -> None: ...

    async def send_participant(
        self, event: Event, participant_id: uuid.UUID
    ) -> None: ...

    async def send_invitation_created(self, invitation: Invitation) -> None:
        await self._producer.send_and_wait(
            topic=INVITATION_CREATED,
            value=InvitationCreated.from_model(invitation),
        )

    async def send_invitation_canceled(self, invitation: Invitation) -> None:
        await self._producer.send_and_wait(
            topic=INVITATION_CANCELED,
            value=InvitationCanceled.from_model(invitation),
        )

    async def send_invitation_accepted(self, invitation: Invitation) -> None:
        await self._producer.send_and_wait(
            topic=INVITATION_ACCEPTED,
            value=InvitationAccepted.from_model(invitation),
        )

    async def send_invitation_rejected(self, invitation: Invitation) -> None:
        await self._producer.send_and_wait(
            topic=INVITATION_REJECTED,
            value=InvitationRejected.from_model(invitation),
        )

    async def send_join_request_created(self, join_request: JoinRequest) -> None:
        await self._producer.send_and_wait(
            topic=JOIN_REQUEST_CREATED,
            value=JoinRequestCreated.from_model(join_request),
        )

    async def send_join_request_canceled(self, join_request: JoinRequest) -> None:
        await self._producer.send_and_wait(
            topic=JOIN_REQUEST_CANCELED,
            value=JoinRequestCanceled.from_model(join_request),
        )

    async def send_join_request_accepted(self, join_request: JoinRequest) -> None:
        await self._producer.send_and_wait(
            topic=JOIN_REQUEST_ACCEPTED,
            value=JoinRequestAccepted.from_model(join_request),
        )

    async def send_join_request_rejected(self, join_request: JoinRequest) -> None:
        await self._producer.send_and_wait(
            topic=JOIN_REQUEST_REJECTED,
            value=JoinRequestRejected.from_model(join_request),
        )
