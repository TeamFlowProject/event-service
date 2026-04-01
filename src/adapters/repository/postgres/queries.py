CREATE_TASK_QUERY = """
    INSERT INTO tracks
    (
        id,
        event_id,
        name,
        description,
        max_team_count,
        max_participants_count,
        min_team_size,
        max_team_size,
        requirements,
        status,
        registration_deadline
    )
    VALUES
    (
        %(id)s,
        %(event_id)s,
        %(name)s,
        %(description)s,
        %(max_team_count)s,
        %(max_participants_count)s,
        %(min_team_size)s,
        %(max_team_size)s,
        %(requirements)s,
        %(status)s,
        %(registration_deadline)s
    )
"""
CREATE_ROLES_QUERY = """
    INSERT INTO roles
    (
        id,
        track_id,
        name,
        description,
        count
    )
    VALUES
    (
        %(id)s,
        %(track_id)s,
        %(name)s,
        %(description)s,
        %(count)s
    )
"""
UPSERT_ROLES_QUERY = """
    INSERT INTO roles(
        id,
        track_id,
        name,
        description,
        count
    )
    VALUES(
        %(id)s,
        %(track_id)s,
        %(name)s,
        %(description)s,
        %(count)s
    )
    ON CONFLICT (id) DO UPDATE
    SET
        name = EXCLUDED.name,
        description = EXCLUDED.description,
        count = EXCLUDED.count
"""
DELETE_STALE_ROLES_QUERY = """
    DELETE FROM roles
    WHERE track_id = %(track_id)s
    AND id != ALL(%(ids)s::uuid[])
"""
UPDATE_TRACKS_QUERY = """
    UPDATE tracks
    SET
        name = %(name)s,
        description = %(description)s,
        max_team_count = %(max_team_count)s,
        max_participants_count = %(max_participants_count)s,
        min_team_size = %(min_team_size)s,
        max_team_size = %(max_team_size)s,
        requirements = %(requirements)s,
        status = %(status)s,
        registration_deadline = %(registration_deadline)s
    WHERE id = %(id)s
"""
DELETE_TRACKS_QUERY = """
    DELETE FROM tracks
    WHERE id = %(id)s
"""
DELETE_ROLES_QUERY = """
    DELETE FROM roles
    WHERE track_id = %(track_id)s
"""
SELECT_TRACKS_QUERY = """
    SELECT
        id,
        event_id,
        name,
        description,
        max_team_count,
        max_participants_count,
        min_team_size,
        max_team_size,
        requirements,
        status,
        registration_deadline
    FROM tracks
    WHERE id = %(id)s
"""
SELECT_ROLES_QUERY = """
    SELECT
        id,
        track_id,
        name,
        description,
        count
    FROM roles
    WHERE track_id = %(track_id)s
"""
SELECT_ROLES_BY_EVENT_ID_QUERY = """
    SELECT
        id,
        track_id,
        name,
        description,
        count
    FROM roles
    WHERE track_id IN (
        SELECT id FROM tracks WHERE event_id = %(event_id)s
    )
"""
SELECT_TRACKS_BY_EVENT_ID_QUERY = """
    SELECT
        id,
        event_id,
        name,
        description,
        max_team_count,
        max_participants_count,
        min_team_size,
        max_team_size,
        requirements,
        status,
        registration_deadline
    FROM tracks
    WHERE event_id = %(event_id)s
"""
