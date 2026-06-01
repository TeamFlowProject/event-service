import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TeamConfirmationPayload(BaseModel):
    """Полезная нагрузка доменного события confirmation-engine.

    ``application_id`` совпадает с ``id`` команды в event-service, так как
    confirmation-engine строит заявку из ``event_service.team.*`` событий.
    Дополнительные поля (``reason``, ``grace_deadline``) присутствуют не во
    всех событиях, поэтому они опциональны.
    """

    application_id: uuid.UUID
    event_id: Optional[uuid.UUID] = None
    occurred_at: Optional[datetime] = None
    reason: Optional[str] = None
    grace_deadline: Optional[datetime] = None


class TeamConfirmationEvent(BaseModel):
    """Outbox-конверт, в котором confirmation-engine публикует событие.

    Само доменное событие лежит во вложенном поле ``payload``; на верхнем
    уровне — метаданные outbox (``aggregate_id`` совпадает с id команды).
    """

    aggregate_type: Optional[str] = None
    aggregate_id: Optional[uuid.UUID] = None
    event_type: Optional[str] = None
    payload: TeamConfirmationPayload
