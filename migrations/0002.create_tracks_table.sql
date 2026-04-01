-- depends: 0001.create_events_table

CREATE TYPE track_status AS ENUM ('DRAFT', 'OPEN', 'FULL', 'CLOSED');

CREATE TABLE IF NOT EXISTS tracks (
    id                      UUID PRIMARY KEY,
    event_id                UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    name                    VARCHAR(255) NOT NULL,
    description             TEXT NOT NULL,
    max_team_count          INTEGER NOT NULL,
    max_participants_count  INTEGER NOT NULL,
    min_team_size           INTEGER NOT NULL,
    max_team_size           INTEGER NOT NULL,
    requirements            TEXT NOT NULL,
    status                  track_status NOT NULL DEFAULT 'DRAFT',
    registration_deadline   TIMESTAMPTZ NOT NULL
);
