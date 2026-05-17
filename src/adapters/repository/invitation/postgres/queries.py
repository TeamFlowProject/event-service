CREATE_INVITATION_QUERY = """
    INSERT INTO invitations (
        id, team_id, owner_id, member_id, role_id, description
    ) VALUES (
        %(id)s, %(team_id)s, %(owner_id)s, %(member_id)s, %(role_id)s, %(description)s
    )
"""

GET_INVITATION_QUERY = """
    SELECT id, team_id, owner_id, member_id, role_id, description
    FROM invitations
    WHERE id = %(id)s
"""

GET_INVITATIONS_BY_TEAM_QUERY = """
    SELECT id, team_id, owner_id, member_id, role_id, description
    FROM invitations
    WHERE team_id = %(team_id)s
"""

GET_INVITATIONS_BY_MEMBER_QUERY = """
    SELECT id, team_id, owner_id, member_id, role_id, description
    FROM invitations
    WHERE member_id = %(member_id)s
"""

DELETE_INVITATION_QUERY = """
    DELETE FROM invitations
    WHERE id = %(id)s
    RETURNING id
"""

DELETE_INVITATIONS_BY_MEMBER_QUERY = """
    DELETE FROM invitations
    WHERE member_id = %(member_id)s
"""

CREATE_JOIN_REQUEST_QUERY = """
    INSERT INTO join_requests (
        id, team_id, owner_id, member_id, role_id, description
    ) VALUES (
        %(id)s, %(team_id)s, %(owner_id)s, %(member_id)s, %(role_id)s, %(description)s
    )
"""

GET_JOIN_REQUEST_QUERY = """
    SELECT id, team_id, owner_id, member_id, role_id, description
    FROM join_requests
    WHERE id = %(id)s
"""

GET_JOIN_REQUESTS_BY_TRACK_AND_MEMBER_QUERY = """
    SELECT jr.id, jr.team_id, jr.owner_id, jr.member_id, jr.role_id, jr.description
    FROM join_requests jr
    JOIN teams t ON t.id = jr.team_id
    WHERE t.track_id = %(track_id)s
      AND jr.member_id = %(member_id)s
"""

GET_JOIN_REQUESTS_BY_MEMBER_QUERY = """
    SELECT id, team_id, owner_id, member_id, role_id, description
    FROM join_requests
    WHERE member_id = %(member_id)s
"""

DELETE_JOIN_REQUEST_QUERY = """
    DELETE FROM join_requests
    WHERE id = %(id)s
    RETURNING id
"""

DELETE_JOIN_REQUESTS_BY_MEMBER_QUERY = """
    DELETE FROM join_requests
    WHERE member_id = %(member_id)s
"""

GET_TEAM_FOR_INVITATION_QUERY = """
    SELECT id, track_id, event_id, owner_id
    FROM teams
    WHERE id = %(id)s
"""

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

GET_ROLE_QUERY = """
    SELECT id, track_id, name, description, count
    FROM roles
    WHERE id = %(id)s
"""

SET_HAVE_TEAM_QUERY = """
    UPDATE event_participants
    SET have_team = %(have_team)s
    WHERE participant_id = %(participant_id)s AND event_id = %(event_id)s
"""

INSERT_TEAM_MEMBER_QUERY = """
    INSERT INTO team_members (team_id, member_id, role_id, joined_at)
    VALUES (%(team_id)s, %(member_id)s, %(role_id)s, NOW())
"""

DECREMENT_TEAM_REQUIRED_COUNT_QUERY = """
    UPDATE team_roles
    SET required_count = required_count - 1
    WHERE team_id = %(team_id)s AND role_id = %(role_id)s
"""

GET_TEAM_ROLES_QUERY = """
    SELECT
        tr.role_id,
        r.track_id,
        r.name,
        r.description,
        tr.required_count
    FROM team_roles tr
    JOIN roles r ON r.id = tr.role_id
    WHERE tr.team_id = %(team_id)s
"""
