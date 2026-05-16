class RepositoryError(Exception):
    ...


class TrackNotFoundError(Exception):
    ...


class EventNotFoundError(Exception):
    ...


class EventAlreadyExistsError(Exception):
    ...


class PaginationError(Exception):
    ...


class ParticipantNotFoundError(Exception):
    ...


class TeamNotFoundError(Exception):
    ...


class TeamAlreadyExistsError(Exception):
    ...
