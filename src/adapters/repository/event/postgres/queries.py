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
    ON CONFLICT (name, surname, patronymic) 
    DO NOTHING  
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
    ORDER BY created_at DESC
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
    ORDER BY p.id DESC, ep.registered_at DESC 
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
    WHERE (created_at, id) < (
        SELECT created_at, id FROM events WHERE id = %(id)s
    )
    ORDER BY created_at DESC, id DESC
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
    ORDER BY p.id DESC, ep.registered_at DESC
    LIMIT %(limit)s
"""
