-- depends: 0004.create_participants_table

CREATE TABLE IF NOT EXISTS event_participants (
    id              UUID PRIMARY KEY,
    event_id        UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    participant_id  UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    have_team       BOOLEAN NOT NULL,
    registered_at   TIMESTAMPTZ NOT NULL
);
