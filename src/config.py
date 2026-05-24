from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", populate_by_name=True
    )

    database_dsn: str = Field(
        default="postgresql://user:password@localhost:5432/event_db",
        alias="DATABASE_DSN",
    )
    database_min_connections: int = Field(default=1, alias="DATABASE_MIN_CONNECTIONS")
    database_max_connections: int = Field(default=10, alias="DATABASE_MAX_CONNECTIONS")
    kafka_bootstrap: str = Field(default="localhost:9092", alias="KAFKA_BOOTSTRAP")
    http_host: str = Field(default="0.0.0.0", alias="HTTP_HOST")
    http_port: int = Field(default=8001, alias="HTTP_PORT")
    kafka_topic_commands: str = Field(
        default="event-commands", alias="KAFKA_TOPIC_COMMANDS"
    )
    kafka_topic_events: str = Field(default="event-events", alias="KAFKA_TOPIC_EVENTS")
    kafka_group_id: str = Field(default="event-service", alias="KAFKA_GROUP_ID")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_json: bool = Field(default=False, alias="LOG_JSON")
    otel_service_name: str = Field(default="event-service", alias="OTEL_SERVICE_NAME")
    otel_exporter_otlp_endpoint: str = Field(
        default="http://localhost:4317",
        alias="OTEL_EXPORTER_OTLP_ENDPOINT",
    )
    otel_enabled: bool = Field(default=True, alias="OTEL_ENABLED")
