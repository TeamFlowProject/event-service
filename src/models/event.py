import uuid
from dataclasses import dataclass


@dataclass
class Event:
    id: uuid.UUID
