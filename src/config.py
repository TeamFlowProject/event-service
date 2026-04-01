from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_dsn: str = "postgresql://user:password@localhost:5432/event_db"
    database_min_connections: int = 1
    database_max_connections: int = 10
    kafka_bootstrap: str = "localhost:9092"
    http_host: str = "0.0.0.0"
    http_port: int = 8001
    kafka_topic_commands: str = "event-commands"
    kafka_topic_events: str = "event-events"
    kafka_group_id: str = "event-service"
    log_level: str = "INFO"
