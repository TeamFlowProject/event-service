-- depends: 0007.create_team_members
CREATE TABLE IF NOT EXISTS team_roles (
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    required_count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (team_id, role_id)
);
