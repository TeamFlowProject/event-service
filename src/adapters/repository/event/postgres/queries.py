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
        FAQ,
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
        %(FAQ)s,
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
"""
REGISTER_PARTICIPANT_QUERY = """
    INSERT INTO event_participants (
        id,
        event_id,
        participant_id,
        have_team,
        registered_at
    )
    VALUES
    (
        %(id)s,
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
        FAQ=%(FAQ)s,
        status=%(status)s
    WHERE id=%(id)s
    RETURNING id
"""
UPDATE_PARTICIPANT_QUERY = """
    UPDATE participants
    SET 
        name=%(name)s,
        surname=%(surname)s,
        patronymic=%(patronymic)s
    WHERE id=%(id)s
    RETURNING id
"""
UPDATE_PARTICIPANT_TEAM_STATUS_QUERY = """
    UPDATE event_participants
    SET 
        have_team=%(have_team)s
    WHERE id=%(id)s
    RETURNING id
"""


DELETE_EVENT_QUERY = """
    DELETE FROM events
    WHERE id=%(id)s
    RETURNING id
"""
DELETE_PARTICIPANT_QUERY = """
    DELETE FROM participants
    WHERE id=%(id)s
    RETURNING id
"""
UNREGISTER_PARTICIPANT_QUERY = """
    DELETE FROM event_participants
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
        FAQ,
        status
    FROM events
    WHERE id=%(id)s
"""
SELECT_PARTICIPANT_QUERY = """
    SELECT
        id,
        name,
        surname,
        patronymic
    FROM participants
    WHERE id=%(id)s
"""
SELECT_EVENTS_QUERY = """
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
        FAQ,
        status
    FROM events
    ORDER BY created_at DESC
"""
SELECT_PARTICIPANTS_QUERY = """
    SELECT
        id,
        name,
        surname,
        patronymic
    FROM participants
"""
SELECT_EVENT_PARTICIPANTS_QUERY = """
    SELECT 
        p.id,
        p.name,
        p.surname,
        p.patronymic,
        ep.have_team,
        ep.registered_at
    FROM event_participants ep
    INNER JOIN participants p ON p.id = ep.participant_id
    WHERE ep.event_id = %(event_id)s
    ORDER BY ep.registered_at DESC
"""
SELECT_PARTICIPANT_EVENTS_QUERY = """
    SELECT
        e.id,
        e.name,
        e.description,
        e.type,
        e.registration_start,
        e.registration_end,
        e.holding_start,
        e.holding_end,
        e.created_at,
        e.organizers,
        e.rules,
        e.FAQ,
        e.status
    FROM event_participants ep
    INNER JOIN events e ON e.id = ep.event_id
    WHERE ep.participant_id = %(participant_id)s
    ORDER BY ep.registered_at DESC
"""


CHECK_REGISTRATION_QUERY = """
    SELECT COUNT(*)
    FROM event_participants
    WHERE event_id=%(event_id)s and participant_id=%(participant_id)s
"""
