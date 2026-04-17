-- depends: 0005.create_participants_table
CREATE TABLE teams (
    id UUID PRIMARY KEY,
    track_id UUID NOT NULL,
    event_id UUID NOT NULL,
    owner_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    required_roles JSONB DEFAULT '[]',
    status VARCHAR(50) NOT NULL DEFAULT 'DRAFT',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    FOREIGN KEY (owner_id) REFERENCES participants(id) ON DELETE CASCADE
);

CREATE INDEX idx_teams_event_id ON teams(event_id);
CREATE INDEX idx_teams_track_id ON teams(track_id);
CREATE INDEX idx_teams_owner_id ON teams(owner_id);
CREATE INDEX idx_teams_status ON teams(status);
