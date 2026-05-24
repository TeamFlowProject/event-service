-- depends: 0008.create_team_roles

CREATE TABLE IF NOT EXISTS invitations (
    id          UUID PRIMARY KEY,
    team_id     UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    owner_id    UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    member_id   UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    role_id     UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    description TEXT NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (team_id, member_id)
);

CREATE INDEX idx_invitations_team_id ON invitations(team_id);
CREATE INDEX idx_invitations_member_id ON invitations(member_id);
CREATE INDEX idx_invitations_owner_id ON invitations(owner_id);
