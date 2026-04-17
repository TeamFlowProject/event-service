CREATE_TEAM_QUERY = """
    INSERT INTO teams (
        id, track_id, event_id, owner_id, name,
        description, required_roles, status, created_at, updated_at
    ) VALUES (
        %(id)s, %(track_id)s, %(event_id)s, %(owner_id)s, %(name)s,
        %(description)s, %(required_roles)s, %(status)s, %(created_at)s, %(updated_at)s
    )
"""

GET_TEAM_QUERY = """
    SELECT id, track_id, event_id, owner_id, name, description,
           required_roles, status, created_at, updated_at
    FROM teams
    WHERE id = %(id)s
"""

UPDATE_TEAM_QUERY = """
    UPDATE teams
    SET name = %(name)s,
        description = %(description)s,
        required_roles = %(required_roles)s,
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

UPDATE_TEAM_STATUS_QUERY = """
    UPDATE teams
    SET status = %(status)s,
        updated_at = NOW()
    WHERE id = %(id)s
    RETURNING id
"""

GET_TEAMS_BY_EVENT_QUERY = """
    SELECT id, track_id, event_id, owner_id, name, description,
           required_roles, status, created_at, updated_at
    FROM teams
    WHERE event_id = %(event_id)s
    ORDER BY created_at DESC
    LIMIT %(limit)s OFFSET %(offset)s
"""

GET_TEAMS_BY_OWNER_QUERY = """
    SELECT id, track_id, event_id, owner_id, name, description,
           required_roles, status, created_at, updated_at
    FROM teams
    WHERE owner_id = %(owner_id)s
    ORDER BY created_at DESC
"""

COUNT_TEAMS_BY_EVENT_QUERY = """
    SELECT COUNT(*) as count
    FROM teams
    WHERE event_id = %(event_id)s
"""

# Team members queries
ADD_TEAM_MEMBER_QUERY = """
    INSERT INTO team_members (team_id, member_id, joined_at)
    VALUES (%(team_id)s, %(member_id)s, %(joined_at)s)
    ON CONFLICT (team_id, member_id) DO NOTHING
"""

REMOVE_TEAM_MEMBER_QUERY = """
    DELETE FROM team_members
    WHERE team_id = %(team_id)s AND member_id = %(member_id)s
    RETURNING member_id
"""

GET_TEAM_MEMBERS_QUERY = """
    SELECT team_id, member_id, joined_at
    FROM team_members
    WHERE team_id = %(team_id)s
"""

CHECK_MEMBER_IN_TEAM_QUERY = """
    SELECT EXISTS(
        SELECT 1 FROM team_members
        WHERE team_id = %(team_id)s AND member_id = %(member_id)s
    )
"""

GET_MEMBER_TEAM_QUERY = """
    SELECT team_id
    FROM team_members
    WHERE member_id = %(member_id)s
    LIMIT 1
"""

GET_PARTICIPANT_BY_ID_QUERY = """
    SELECT id, name, surname, patronymic
    FROM participants
    WHERE id = %(id)s
"""

GET_PARTICIPANT_WITH_TEAM_STATUS_QUERY = """
    SELECT
        p.id,
        p.name,
        p.surname,
        p.patronymic,
        EXISTS(
            SELECT 1 FROM team_members tm
            WHERE tm.member_id = p.id
        ) as have_team
    FROM participants p
    WHERE p.id = %(id)s
"""
