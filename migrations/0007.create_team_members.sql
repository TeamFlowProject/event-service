-- depends: 0006.create_teams_table
CREATE TABLE team_members (
    team_id UUID NOT NULL,
    member_id UUID NOT NULL,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
    joined_at TIMESTAMP NOT NULL DEFAULT NOW(),

    PRIMARY KEY (team_id, member_id),

    FOREIGN KEY (team_id) REFERENCES teams (id) ON DELETE CASCADE,
    FOREIGN KEY (member_id) REFERENCES participants (id) ON DELETE CASCADE
);

CREATE INDEX idx_team_members_member_id ON team_members (member_id);
CREATE INDEX idx_team_members_team_id ON team_members (team_id);
