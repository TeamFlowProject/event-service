# event-service

Сервис событий, треков и участников (TeamFlow).

## Переменные окружения (Docker Compose)

Для **каждого** сервиса в `compose.yaml` — свой файл (в git не попадают, кроме example):

| Сервис | Файл |
|--------|------|
| KrakenD | `.env_krakend` |
| event-service | `.env_event_service` |
| PostgreSQL | `.env_postgres` |
| Redpanda | `.env_redpanda` |
| Redpanda Console | `.env_redpanda_console` |
| Jaeger | `.env_jaeger` |
| Prometheus | `.env_prometheus` |
| Grafana | `.env_grafana` |
| Loki | `.env_loki` |
| Promtail | `.env_promtail` |

В репозитории только **`.env_event_service.example`**.

Создать все файлы одной командой:

```bash
make init-env
```

Или вручную: `cp .env_event_service.example .env_event_service` и дописать остальные по таблице выше / из `make init-env`.

## Локальный запуск (Docker Compose)

```bash
make init-env
make compose-up
```

Остановка:

```bash
make compose-down
```

`make compose-up` передаёт все `.env_*` в `docker compose`, чтобы подставлялись порты и параметры из каждого файла.

### Точки входа

| Сервис | URL |
|--------|-----|
| API Gateway (KrakenD) | http://localhost:8000 |
| Event Service (напрямую) | http://localhost:8001 |
| Redpanda Console | http://localhost:8080 |
| Jaeger UI | http://localhost:16686 |
| Grafana | http://localhost:3000 |
| Prometheus | http://localhost:9090 |

HTTP API через gateway: `http://localhost:8000/api/v1/...`

## Разработка без Docker

```bash
cp .env_event_service.example .env_event_service
# для локального Postgres/Kafka поправьте DATABASE_DSN и KAFKA_BOOTSTRAP

uv sync
uv run python -m src.main migrate
uv run python -m src.main run
```

## Make

```bash
make lint-fix && make lint
make unit-test
make integration-test
make compose-config   # проверка compose.yaml
```
