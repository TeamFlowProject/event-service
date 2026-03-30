import uuid

from dataclasses import dataclass


@dataclass
class Track:
    id: uuid.UUID
