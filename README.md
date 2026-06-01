# event-service

Центральный сервис платформы **TeamFlow** — отвечает за хакатоны/практики (события), треки,
участников, команды, приглашения и заявки на вступление. Это «источник правды» о том, кто, в каком
событии, в каком треке и в какой команде состоит. Сервис публикует доменные события в Kafka, на
которые реагирует [`confirmation-engine`](../confirmation-engine), и потребляет обратные события о
результатах подтверждения команд.

- **Язык / рантайм:** Python 3.13
- **HTTP-фреймворк:** FastAPI + Uvicorn
- **Хранилище:** PostgreSQL (пул `psycopg` + сборка SQL через PyPika)
- **Шина событий:** Kafka (через `aiokafka`; локально — Redpanda)
- **Миграции:** yoyo-migrations
- **Наблюдаемость:** OpenTelemetry (трейсинг в Jaeger), Prometheus-метрики, структурные логи (loguru), Loki/Promtail
- **Порт по умолчанию:** `8001`

---

## Содержание

- [Архитектура](#архитектура)
- [Структура каталогов](#структура-каталогов)
- [Доменная модель](#доменная-модель)
- [HTTP API](#http-api)
- [Событийная модель (Kafka)](#событийная-модель-kafka)
- [Конфигурация](#конфигурация)
- [Быстрый старт](#быстрый-старт)
- [Миграции БД](#миграции-бд)
- [Тесты](#тесты)
- [Линт и форматирование](#линт-и-форматирование)
- [Наблюдаемость](#наблюдаемость)
- [CI/CD](#cicd)

---

## Архитектура

Сервис построен по принципам **гексагональной (портов и адаптеров) / чистой архитектуры**.
Зависимости направлены строго внутрь: контроллеры знают о сервисах, сервисы — о протоколах
(портах), а конкретные адаптеры реализуют эти протоколы.

```
            ┌──────────────────── controller ────────────────────┐
 HTTP  ───▶ │  controller/http/{event,track,team,invitation}      │
 Kafka ───▶ │  controller/kafka/event_consumer                    │
            └───────────────────────┬─────────────────────────────┘
                                    │  (вызывает по протоколам)
            ┌───────────────────────▼─────────────────────────────┐
            │  service/{event,track,team,invitation}  — бизнес-логика
            └───────────────────────┬─────────────────────────────┘
                                    │  (порты: protocols.py)
            ┌───────────────────────▼─────────────────────────────┐
   adapters │  repository/*/postgres   clients/kafka_producer      │
            └──────────┬──────────────────────────┬───────────────┘
                       ▼                           ▼
                  PostgreSQL                     Kafka
```

- **`models/`** — доменные сущности (обычные `@dataclass`, без зависимости от инфраструктуры).
- **`service/`** — сценарии использования; каждый поддомен описывает свои порты в `protocols.py`
  и кидает доменные ошибки из `service/errors.py`.
- **`adapters/repository/`** — реализации репозиториев поверх PostgreSQL (`queries.py` собирает SQL
  через PyPika, `models.py` маппит строки, `repository.py` оркестрирует пул соединений).
- **`adapters/clients/`** — внешние клиенты, в первую очередь Kafka-продюсер и DTO событий.
- **`controller/`** — точки входа: HTTP-роутеры FastAPI и Kafka-консьюмер.
- **`core/`** — кросс-срезовые вещи: настройка трейсинга и реестр Prometheus-метрик.

Приложение собирается и запускается в [`src/application.py`](src/application.py): поднимает пул
соединений к БД, Kafka-продюсер и консьюмер, регистрирует роутеры, middleware наблюдаемости и
эндпоинт `/metrics`, после чего параллельно (`asyncio.gather`) обслуживает HTTP-сервер и
Kafka-консьюмер.

## Структура каталогов

```
src/
├── main.py                  # Typer-CLI: run / migrate / migrate-down / migrate-drop
├── application.py           # сборка и запуск всех компонентов
├── config.py                # Pydantic Settings (читает .env)
├── core/
│   ├── tracing.py           # инициализация OpenTelemetry
│   └── metrics.py           # Prometheus-метрики и эндпоинт /metrics
├── models/                  # доменные сущности: event, track, team, invitation
├── controller/
│   ├── middleware.py        # ObservabilityMiddleware (метрики + трейсы для HTTP)
│   ├── http/{event,track,team,invitation}/  # роутеры, схемы (pydantic), протоколы
│   └── kafka/               # event_consumer, dto, protocols
├── service/{event,track,team,invitation}/   # бизнес-логика + порты
└── adapters/
    ├── repository/{event,track,team,invitation}/postgres/
    └── clients/             # kafka_producer + dto/{event,track,team,invitation}
migrations/                  # SQL-миграции yoyo (NNNN.<name>.sql + .rollback.sql)
tests/
├── unit/                    # сервисы и роутеры (моки портов)
└── integration/             # репозитории и Kafka на testcontainers
```

## Доменная модель

| Сущность | Ключевые поля | Статусы |
|----------|---------------|---------|
| **Event** | `name`, `description`, `type`, окна регистрации и проведения, `organizers`, `rules`, `faq` | `DRAFT → OPEN → FULL → CLOSED` |
| **Track** | `event_id`, лимиты команд/участников, `min/max_team_size`, `required_roles`, `requirements`, `registration_deadline` | `DRAFT / OPEN / FULL / CLOSED` |
| **Role** | `track_id`, `name`, `description`, `count` (сколько таких ролей нужно в команде) | — |
| **Participant** | `event_id`, ФИО, `have_team`, `role_id` | — |
| **Team** | `track_id`, `event_id`, `owner`, `members`, `required_roles` | `DRAFT → BUILDING → FULL → SUBMITTED → VALIDATED → CONFIRMED / REJECTED / INVALID` |
| **Invitation** | `team_id`, `owner`, `member`, `role` | приглашение от команды участнику |
| **JoinRequest** | `team_id`, `owner`, `member`, `role` | заявка участника в команду |

Тип события (`EventTypeEnum`): `HACKATHON`, `PRACTICE`.

Жизненный цикл команды: участники собирают команду (`BUILDING`), затем владелец отправляет её на
проверку (`SUBMITTED`). Дальше статусы `VALIDATED / CONFIRMED / REJECTED / INVALID` проставляются
**асинхронно** по событиям от `confirmation-engine` (см. ниже).

## HTTP API

Все маршруты под префиксом `/api/v1`. Идентификация пользователя — через заголовок `X-User-Id`
(UUID); его отсутствие там, где он требуется, даёт `401`. Идентификаторы создаваемых ресурсов —
UUIDv7 (монотонно растущие). Интерактивная документация: `GET /docs` (Swagger) и `GET /openapi.json`.

### События
| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/events` | Создать событие → `201 {id}` |
| `GET` | `/events` | Список событий (пагинация) |
| `GET` | `/events/{event_id}` | Получить событие |
| `PUT` | `/events/{event_id}` | Обновить событие |
| `DELETE` | `/events/{event_id}` | Удалить событие → `204` |
| `POST` | `/events/{event_id}/participants` | Зарегистрировать участника |
| `GET` | `/participants/{participant_id}/events` | События участника (пагинация) |

### Треки
| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/track` | Создать трек |
| `GET` | `/track/{track_id}` | Получить трек |
| `GET` | `/event/{event_id}/tracks` | Треки события |
| `PUT` | `/track/{track_id}` | Обновить трек |
| `DELETE` | `/track/{track_id}` | Удалить трек |

### Команды
| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/teams` | Создать команду |
| `GET` | `/teams/{id}` | Получить команду |
| `PUT` | `/teams/{team_id}` | Обновить команду |
| `DELETE` | `/teams/{id}` | Удалить команду |
| `POST` | `/teams/{team_id}/submission` | Отправить команду на подтверждение |
| `GET` | `/event/{event_id}/teams` | Команды события |
| `GET` | `/user/{user_id}/teams` | Команды пользователя |
| `GET` | `/user/{user_id}/event/{event_id}/team` | Команда пользователя в событии |
| `DELETE` | `/team/member/{user_id}` | Исключить участника / выход из команды |
| `PUT` | `/teams/{team_id}/members/{member_id}/role` | Сменить роль участника |

### Приглашения и заявки
| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/invitations` | Пригласить участника в команду |
| `GET` | `/invitations/{invitation_id}` | Получить приглашение |
| `GET` | `/teams/{team_id}/invitations` | Приглашения команды |
| `GET` | `/users/{user_id}/invitations` | Приглашения пользователя |
| `PUT` | `/invitations/{invitation_id}` | Принять/отклонить приглашение |
| `DELETE` | `/invitations/{invitation_id}` | Отозвать приглашение |
| `POST` | `/join_requests` | Подать заявку на вступление |
| `GET` | `/join_requests/...` | Заявки (по команде/пользователю) |
| `PUT` | `/join_requests/{join_request_id}` | Принять/отклонить заявку |
| `DELETE` | `/join_requests/{join_request_id}` | Отменить заявку |

Служебное: `GET /metrics` — метрики Prometheus.

## Событийная модель (Kafka)

Сервис придерживается модели «команда меняет состояние → публикуется событие». Имена топиков
заданы в [`src/adapters/clients/topics.py`](src/adapters/clients/topics.py).

**Публикует** (`event_service.*`):

- Треки: `track.created`, `track.updated`, `track.deleted`
- Приглашения: `invitation.created|canceled|accepted|rejected`
- Заявки: `join_request.created|canceled|accepted|rejected`
- Команды: `team.created|updated|deleted|submitted`, `team.member.left|kicked|role_changed`
- События: `event.created|updated|deleted`, `event.participant`

**Потребляет** (от `confirmation-engine`, группа `KAFKA_CONFIRMATION_GROUP_ID`):

| Топик | Новый статус команды |
|-------|----------------------|
| `confirmation_engine.team.validated` | `VALIDATED` |
| `confirmation_engine.team.confirmed` | `CONFIRMED` |
| `confirmation_engine.team.rejected` | `REJECTED` |
| `confirmation_engine.team.became_invalid` | `INVALID` |

Консьюмер ([`controller/kafka/event_consumer.py`](src/controller/kafka/event_consumer.py)) работает
с **ручным коммитом оффсетов**: успешно обработанное либо «пропускаемое» (например, команда не
найдена) сообщение коммитится, а при неожиданной ошибке делается `seek` назад на тот же оффсет для
повторной обработки. Контекст трейсинга прокидывается через Kafka-заголовки (W3C propagation).

## Конфигурация

Конфиг читается из `.env` (см. [`.env.example`](.env.example)) через `pydantic-settings`.

| Переменная | По умолчанию | Назначение |
|------------|--------------|------------|
| `HTTP_HOST` / `HTTP_PORT` | `0.0.0.0` / `8001` | адрес HTTP-сервера |
| `DATABASE_DSN` | `postgresql://user:password@localhost:5432/event_db` | DSN PostgreSQL |
| `DATABASE_MIN_CONNECTIONS` / `DATABASE_MAX_CONNECTIONS` | `1` / `10` | размер пула соединений |
| `KAFKA_BOOTSTRAP` | `localhost:9092` | брокеры Kafka |
| `KAFKA_TOPIC_COMMANDS` / `KAFKA_TOPIC_EVENTS` | `event-commands` / `event-events` | имена топиков |
| `KAFKA_GROUP_ID` | `event-service` | группа консьюмера |
| `KAFKA_CONFIRMATION_GROUP_ID` | `event-service-confirmation` | группа для событий confirmation-engine |
| `LOG_LEVEL` | `INFO` | уровень логирования |
| `LOG_JSON` | `false` | структурный JSON-лог (для Loki) вместо человекочитаемого |
| `OTEL_ENABLED` | `true` | включить трейсинг |
| `OTEL_SERVICE_NAME` | `event-service` | имя сервиса в трейсах |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | OTLP-коллектор (Jaeger) |

## Быстрый старт

Зависимости менеджит [`uv`](https://docs.astral.sh/uv/).

```bash
# 1. Установить зависимости
uv sync

# 2. Поднять инфраструктуру (Postgres, Redpanda, Jaeger, Prometheus, Grafana, Loki)
docker compose up -d postgres redpanda jaeger prometheus grafana loki

# 3. Скопировать и при необходимости отредактировать конфиг
cp .env.example .env

# 4. Применить миграции
make migrate-up        # = python -m src.main migrate

# 5. Запустить сервис
make run               # = python -m src.main run
```

Сервис будет доступен на `http://localhost:8001` (Swagger — `/docs`).

Запуск целиком в Docker:

```bash
docker compose up --build
```

> Полный продакшен-подобный запуск всей платформы (все сервисы + KrakenD + Keycloak) — в репозитории
> [`compose`](../compose).

## Миграции БД

Миграции — обычные SQL-файлы в `migrations/`, парами `NNNN.<name>.sql` + `NNNN.<name>.rollback.sql`,
с указанием зависимостей через `-- depends:`. Управляются через CLI:

```bash
make migrate-up      # применить все ожидающие миграции
make migrate-down    # откатить последнюю
make migrate-drop    # откатить все
```

Схема включает: `events`, `tracks`, `roles`, `participants`, `event_participants`, `teams`,
`team_members`, `team_roles`, `invitations`, `join_requests`.

## Тесты

```bash
make unit-test          # юнит-тесты (-m unit), с покрытием
make integration-test   # интеграционные (-m integration): Postgres/Kafka в testcontainers
make test               # всё вместе
```

Интеграционные тесты используют `testcontainers[postgres]`, поэтому требуется запущенный Docker.

## Линт и форматирование

```bash
make install-tools   # uv tool install pyright ruff
make lint            # pyright + ruff check + ruff format --check
make lint-fix        # ruff check --fix + ruff format
```

В репозитории настроен `pre-commit` ([`.pre-commit-config.yaml`](.pre-commit-config.yaml)).

## Наблюдаемость

- **Трейсинг.** OpenTelemetry с автоинструментацией FastAPI; спаны экспортируются по OTLP/gRPC в
  Jaeger (`http://localhost:16686`). Контекст пробрасывается и через Kafka-заголовки.
- **Метрики.** Prometheus-эндпоинт `/metrics`. Среди метрик: `http_requests_total`,
  `http_request_duration_seconds`, `business_operations_total`, `db_query_duration_seconds`,
  `kafka_messages_sent_total`, `kafka_messages_consumed_total`. Дашборды — в Grafana
  (`http://localhost:3000`).
- **Логи.** `loguru`; при `LOG_JSON=true` — однострочный JSON, который собирает Promtail в Loki.

## CI/CD

GitHub Actions (`.github/workflows`) переиспользует общие шаблоны из
[`cicd-templates`](../cicd-templates): линт (ruff + pyright), юнит- и интеграционные тесты. Запуск —
на push/PR в `main` и `develop`.
