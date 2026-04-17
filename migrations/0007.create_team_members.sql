-- depends: 0006.create_teams_table
CREATE TABLE team_members (
    team_id UUID NOT NULL,
    member_id UUID NOT NULL,
    joined_at TIMESTAMP NOT NULL DEFAULT NOW(),

    PRIMARY KEY (team_id, member_id),

    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
    FOREIGN KEY (member_id) REFERENCES participants(id) ON DELETE CASCADE,

    INDEX idx_team_members_member_id (member_id),
    INDEX idx_team_members_team_id (team_id)
);
