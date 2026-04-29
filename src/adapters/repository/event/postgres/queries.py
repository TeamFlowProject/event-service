CREATE_EVENT_QUERY = """
    INSERT INTO events (
        id,
        name,
        description,
        type,
        registration_start,
        registration_end,
        holding_start,
        holding_end,
        created_at,
        organizers,
        rules,
        faq,
        status
    ) 
    VALUES 
    (
        %(id)s,
        %(name)s,
        %(description)s,
        %(type)s,
        %(registration_start)s,
        %(registration_end)s,
        %(holding_start)s,
        %(holding_end)s,
        %(created_at)s,
        %(organizers)s,
        %(rules)s,
        %(faq)s,
        %(status)s
    )
"""
CREATE_PARTICIPANT_QUERY = """
    INSERT INTO participants (
        id,
        name,
        surname,
        patronymic
    )
    VALUES
    (
        %(id)s,
        %(name)s,
        %(surname)s,
        %(patronymic)s
    )
    ON CONFLICT (id)
    DO NOTHING
"""
REGISTER_PARTICIPANT_QUERY = """
    INSERT INTO event_participants (
        event_id,
        participant_id,
        have_team,
        registered_at
    )
    VALUES
    (
        %(event_id)s,
        %(participant_id)s,
        %(have_team)s,
        %(registered_at)s
    )
"""


UPDATE_EVENT_QUERY = """
    UPDATE events
    SET
        name=%(name)s,
        description=%(description)s,
        type=%(type)s,
        registration_start=%(registration_start)s,
        registration_end=%(registration_end)s,
        holding_start=%(holding_start)s,
        holding_end=%(holding_end)s,
        organizers=%(organizers)s,
        rules=%(rules)s,
        faq=%(faq)s,
        status=%(status)s
    WHERE id=%(id)s
    RETURNING id
"""

DELETE_EVENT_QUERY = """
    DELETE FROM events
    WHERE id=%(id)s
    RETURNING id
"""

SELECT_EVENT_QUERY = """
    SELECT
        id,
        name,
        description,
        type,
        registration_start,
        registration_end,
        holding_start,
        holding_end,
        created_at,
        organizers,
        rules,
        faq,
        status
    FROM events
    WHERE id=%(id)s
"""
SELECT_EVENTS_QUERY_BY_NUM = """
    SELECT
        id,
        name,
        description,
        type,
        registration_start,
        registration_end,
        holding_start,
        holding_end,
        created_at,
        organizers,
        rules,
        faq,
        status
    FROM events
    ORDER BY id DESC
    OFFSET %(offset)s LIMIT %(limit)s
"""
SELECT_PARTICIPANTS_QUERY_BY_NUM = """
    SELECT
        p.id,
        p.name,
        p.surname,
        p.patronymic,
        ep.have_team
    FROM event_participants ep
    INNER JOIN participants p ON p.id = ep.participant_id
    WHERE ep.event_id = %(event_id)s
    ORDER BY p.id DESC
    OFFSET %(offset)s LIMIT %(limit)s
"""
SELECT_EVENTS_QUERY_BY_ID = """
    SELECT
        id,
        name,
        description,
        type,
        registration_start,
        registration_end,
        holding_start,
        holding_end,
        created_at,
        organizers,
        rules,
        faq,
        status
    FROM events
    WHERE id < %(id)s
    ORDER BY id DESC
    LIMIT %(limit)s
"""
SELECT_PARTICIPANTS_QUERY_BY_ID = """
    SELECT
        p.id,
        p.name,
        p.surname,
        p.patronymic,
        ep.have_team
    FROM event_participants ep
    INNER JOIN participants p ON p.id = ep.participant_id
    WHERE p.id < %(participant_id)s
      AND ep.event_id = %(event_id)s
    ORDER BY p.id DESC
    LIMIT %(limit)s
"""
SELECT_PARTICIPANT_EVENTS_QUERY_BY_ID = """
    SELECT
        e.id,
        e.name,
        e.description,
        e.registration_start,
        e.registration_end,
        e.holding_start,
        e.holding_end,
        e.status,
        COALESCE((
            SELECT SUM(t.max_participants_count)::int
            FROM tracks t
            WHERE t.event_id = e.id
        ), 0) AS total_places,
        (
            SELECT COUNT(*)::int
            FROM event_participants ep2
            WHERE ep2.event_id = e.id
        ) AS current_participants,
        (
            SELECT COUNT(*)::int
            FROM tracks t2
            WHERE t2.event_id = e.id
        ) AS tracks_count,
        'PARTICIPANT'::text AS user_role
    FROM events e
    INNER JOIN event_participants ep ON ep.event_id = e.id
    WHERE ep.participant_id = %(participant_id)s
      AND e.id < %(event_id)s
    ORDER BY e.id DESC
    LIMIT %(limit)s
"""
SELECT_PARTICIPANT_EVENTS_QUERY_BY_NUM = """
    SELECT
        e.id,
        e.name,
        e.description,
        e.registration_start,
        e.registration_end,
        e.holding_start,
        e.holding_end,
        e.status,
        COALESCE((
            SELECT SUM(t.max_participants_count)::int
            FROM tracks t
            WHERE t.event_id = e.id
        ), 0) AS total_places,
        (
            SELECT COUNT(*)::int
            FROM event_participants ep2
            WHERE ep2.event_id = e.id
        ) AS current_participants,
        (
            SELECT COUNT(*)::int
            FROM tracks t2
            WHERE t2.event_id = e.id
        ) AS tracks_count,
        'PARTICIPANT'::text AS user_role
    FROM events e
    INNER JOIN event_participants ep ON ep.event_id = e.id
    WHERE ep.participant_id = %(participant_id)s
    ORDER BY e.id DESC
    OFFSET %(offset)s LIMIT %(limit)s
"""
