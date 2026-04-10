-- depends:

CREATE TYPE event_type AS ENUM ('HACKATHON', 'PRACTICE');
CREATE TYPE event_status AS ENUM ('DRAFT', 'OPEN', 'FULL', 'CLOSED');

CREATE TABLE IF NOT EXISTS events (
    id                 UUID PRIMARY KEY,
    name               VARCHAR(255) NOT NULL,
    description TEXT   NOT NULL,
    type event_type    NOT NULL,
    registration_start TIMESTAMPTZ NOT NULL,
    registration_end   TIMESTAMPTZ NOT NULL,
    holding_start      TIMESTAMPTZ NOT NULL,
    holding_end        TIMESTAMPTZ NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL,
    organizers         TEXT[] NOT NULL,
    rules              VARCHAR(255) NOT NULL,
    FAQ                VARCHAR(255) NOT NULL,
    status             event_status NOT NULL DEFAULT 'DRAFT'
);
