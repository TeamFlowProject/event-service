# import pytest
# import uuid
# from datetime import datetime, timezone
# from typing import AsyncGenerator

# from src.adapters.repository.team.postgres.repository import TeamPostgresRepository
# from src.adapters.repository.errors import TeamNotFoundError, ParticipantNotFoundError, TeamAlreadyExistsError
# from src.models.team import Team, TeamStatusEnum
# from src.models.event import Participant
# from src.models.track import Role


# @pytest.fixture
# async def team_repository(db_pool) -> AsyncGenerator:
#     """Фикстура для репозитория команд"""
#     repo = TeamPostgresRepository(db_pool)
#     yield repo


# @pytest.fixture
# async def test_event_id(db_pool) -> uuid.UUID:
#     """Создание тестового события"""
#     event_id = uuid.uuid4()
#     # Опционально: создать запись в таблице events, если она есть
#     return event_id


# @pytest.fixture
# async def test_track_id() -> uuid.UUID:
#     """Создание тестового трека"""
#     return uuid.uuid4()


# @pytest.fixture
# async def test_participant(db_pool, test_event_id) -> Participant:
#     """Создание тестового участника"""
#     participant_id = uuid.uuid4()
#     async with db_pool.connection() as conn:
#         async with conn.cursor() as cursor:
#             await cursor.execute("""
#                 INSERT INTO participants (id, event_id, name, surname, patronymic)
#                 VALUES (%s, %s, %s, %s, %s)
#             """, (str(participant_id), str(test_event_id), "Sam", "Smith", "Smith"))

#     return Participant(
#         id=participant_id,
#         event_id=test_event_id,
#         name="Sam",
#         surname="Smith",
#         patronymic="Oliver",
#         have_team=False,
#     )


# @pytest.fixture
# async def test_participant2(db_pool, test_event_id) -> Participant:
#     """Создание второго тестового участника"""
#     participant_id = uuid.uuid4()
#     async with db_pool.connection() as conn:
#         async with conn.cursor() as cursor:
#             await cursor.execute("""
#                 INSERT INTO participants (id, event_id, name, surname, patronymic)
#                 VALUES (%s, %s, %s, %s, %s)
#             """, (str(participant_id), str(test_event_id), "Gabi", "Brown", "Jane"))

#     return Participant(
#         id=participant_id,
#         event_id=test_event_id,
#         name="Gabi",
#         surname="Brown",
#         patronymic="Jane",
#         have_team=False,
#     )


# @pytest.fixture
# async def test_participant3(db_pool, test_event_id) -> Participant:
#     """Создание третьего тестового участника"""
#     participant_id = uuid.uuid4()
#     async with db_pool.connection() as conn:
#         async with conn.cursor() as cursor:
#             await cursor.execute("""
#                 INSERT INTO participants (id, event_id, name, surname, patronymic)
#                 VALUES (%s, %s, %s, %s, %s)
#             """, (str(participant_id), str(test_event_id), "Bob", "Johnson", "Lee"))

#     return Participant(
#         id=participant_id,
#         event_id=test_event_id,
#         name="Bob",
#         surname="Johnson",
#         patronymic="Lee",
#         have_team=False,
#     )


# @pytest.fixture
# async def test_role(test_track_id) -> Role:
#     """Создание тестовой роли"""
#     return Role(
#         id=uuid.uuid4(),
#         track_id=test_track_id,
#         name="Developer",
#         description="Main developer role",
#         count=2,
#     )


# @pytest.fixture
# async def test_team_data(test_participant, test_event_id, test_track_id, test_role) -> dict:
#     """Тестовые данные команды"""
#     return {
#         "id": uuid.uuid4(),
#         "track_id": test_track_id,
#         "event_id": test_event_id,
#         "owner": test_participant,
#         "name": "Test Team",
#         "description": "Test Description",
#         "required_roles": [test_role],
#         "status": TeamStatusEnum.DRAFT,
#         "created_at": datetime.now(timezone.utc),
#         "updated_at": datetime.now(timezone.utc),
#     }
