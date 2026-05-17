-- depends: 0009.create_invitations_table

CREATE TABLE IF NOT EXISTS join_requests (
    id          UUID PRIMARY KEY,
    team_id     UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    owner_id    UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    member_id   UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    role_id     UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    description TEXT NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (team_id, member_id)
);

CREATE INDEX idx_join_requests_team_id ON join_requests(team_id);
CREATE INDEX idx_join_requests_member_id ON join_requests(member_id);
CREATE INDEX idx_join_requests_owner_id ON join_requests(owner_id);
