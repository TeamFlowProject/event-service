CREATE_TEAM_QUERY = """
    INSERT INTO teams (
        id, track_id, event_id, owner_id, owner_role_id, name,
        description, status, created_at, updated_at
    ) VALUES (
        %(id)s, %(track_id)s, %(event_id)s, %(owner_id)s, %(owner_role_id)s, %(name)s,
        %(description)s, %(status)s, %(created_at)s, %(updated_at)s
    )
"""

GET_TEAM_QUERY = """
    SELECT id, track_id, event_id, owner_id, owner_role_id, name, description,
           status, created_at, updated_at
    FROM teams
    WHERE id = %(id)s
"""
GET_TEAM_QUERY_BY_EVENT_ID = """
    SELECT id, track_id, event_id, owner_id, owner_role_id, name, description,
            status, created_at, updated_at
    FROM teams
    WHERE event_id = %(event_id)s
"""
GET_TEAM_QUERY_BY_USER_ID = """
    SELECT id, track_id, event_id, owner_id, owner_role_id, name, description,
            status, created_at, updated_at
    FROM teams
    WHERE owner_id = %(user_id)s
    OR id IN (
                SELECT tm.team_id
                FROM team_members tm
                WHERE tm.member_id = %(user_id)s
            )
"""
GET_USER_TEAM_IN_EVENT = """
    SELECT id, track_id, event_id, owner_id, owner_role_id, name, description,
            status, created_at, updated_at
    FROM teams
    WHERE event_id = %(event_id)s
    AND (owner_id = %(user_id)s
        OR id IN (
            SELECT team_id
            FROM team_members tm
            WHERE member_id = %(user_id)s
        ))
    LIMIT 1
"""

CHANGE_OWNER_ROLE_QUERY = """
    UPDATE teams
    SET owner_role_id = %(role_id)s,
        updated_at = NOW()
    WHERE id = %(team_id)s
    RETURNING id
"""

CHANGE_MEMBER_ROLE_QUERY = """
    UPDATE team_members
    SET role_id = %(role_id)s
    WHERE team_id = %(team_id)s AND member_id = %(member_id)s
    RETURNING member_id
"""

UPDATE_TEAM_QUERY = """
    UPDATE teams
    SET name = %(name)s,
        description = %(description)s,
        status = %(status)s,
        updated_at = NOW()
    WHERE id = %(id)s
    RETURNING id
"""

DELETE_TEAM_QUERY = """
    DELETE FROM teams
    WHERE id = %(id)s
    RETURNING id
"""

CHANGE_TEAM_STATUS_QUERY = """
    UPDATE teams
    SET status = %(status)s,
        updated_at = NOW()
    WHERE id = %(id)s
    RETURNING id
"""

# Team members
INSERT_TEAM_MEMBER_QUERY = """
    INSERT INTO team_members (team_id, member_id, role_id, joined_at)
    VALUES (%(team_id)s, %(member_id)s, %(role_id)s, NOW())
    ON CONFLICT (team_id, member_id) DO NOTHING
"""

REMOVE_TEAM_MEMBER_QUERY = """
    DELETE FROM team_members
    WHERE team_id = %(team_id)s AND member_id = %(member_id)s
    RETURNING member_id, role_id
"""

GET_TEAM_MEMBERS_QUERY = """
    SELECT
        p.id,
        p.name,
        p.surname,
        p.patronymic,
        ep.have_team,
        ep.event_id,
        tm.role_id
    FROM team_members tm
    JOIN participants p ON p.id = tm.member_id
    JOIN event_participants ep
        ON ep.participant_id = p.id AND ep.event_id = %(event_id)s
    WHERE tm.team_id = %(team_id)s
"""

GET_MEMBER_ROLE_IN_TEAM_QUERY = """
    SELECT role_id
    FROM team_members
    WHERE team_id = %(team_id)s AND member_id = %(member_id)s
"""

GET_OWNER_ROLE_IN_TEAM_QUERY = """
    SELECT owner_role_id
    FROM teams
    WHERE id = %(team_id)s
"""

# Team roles
INSERT_TEAM_ROLE_QUERY = """
    INSERT INTO team_roles (team_id, role_id, required_count)
    VALUES (%(team_id)s, %(role_id)s, %(required_count)s)
"""

DELETE_TEAM_ROLES_QUERY = """
    DELETE FROM team_roles WHERE team_id = %(team_id)s
"""

GET_TEAM_ROLES_QUERY = """
    SELECT
        tr.role_id,
        r.track_id,
        r.name,
        r.description,
        r.count,
        tr.required_count
    FROM team_roles tr
    JOIN roles r ON r.id = tr.role_id
    WHERE tr.team_id = %(team_id)s
"""

DECREMENT_REQUIRED_COUNT_QUERY = """
    UPDATE team_roles
    SET required_count = required_count - 1
    WHERE team_id = %(team_id)s AND role_id = %(role_id)s
"""

INCREMENT_REQUIRED_COUNT_QUERY = """
    UPDATE team_roles
    SET required_count = required_count + 1
    WHERE team_id = %(team_id)s AND role_id = %(role_id)s
"""

GET_ROLES_BY_TRACK_QUERY = """
    SELECT id, track_id, name, description, count
    FROM roles
    WHERE track_id = %(track_id)s
"""

# Participants
GET_PARTICIPANT_QUERY = """
    SELECT
        p.id,
        p.name,
        p.surname,
        p.patronymic,
        ep.have_team,
        ep.event_id
    FROM participants p
    JOIN event_participants ep
        ON ep.participant_id = p.id AND ep.event_id = %(event_id)s
    WHERE p.id = %(id)s
"""


SET_HAVE_TEAM_QUERY = """
    UPDATE event_participants
    SET have_team = %(have_team)s
    WHERE participant_id = %(participant_id)s AND event_id = %(event_id)s
"""

RESET_TEAM_MEMBERS_HAVE_TEAM_QUERY = """
    UPDATE event_participants
    SET have_team = FALSE
    WHERE event_id = %(event_id)s
      AND participant_id IN (
        SELECT member_id FROM team_members WHERE team_id = %(team_id)s
    )
"""
