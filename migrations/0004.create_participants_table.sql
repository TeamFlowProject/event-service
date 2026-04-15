-- depends: 0001.create_events_table

CREATE TABLE IF NOT EXISTS participants (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    surname VARCHAR(255) NOT NULL,
    patronymic VARCHAR(255) NOT NULL
);

