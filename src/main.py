import asyncio
import sys

import typer
from loguru import logger
from src.config import Settings
from src.application import run_application

from migrations.migrate import down, drop, up


app = typer.Typer()


def _setup_logger(settings: Settings) -> None:
    logger.remove()
    if settings.log_json:
        import json

        def _json_sink(message) -> None:
            record = message.record
            print(
                json.dumps(
                    {
                        "time": record["time"].isoformat(),
                        "level": record["level"].name,
                        "name": record["name"],
                        "line": record["line"],
                        "message": record["message"],
                        **record["extra"],
                    },
                    default=str,
                ),
                flush=True,
            )

        logger.add(_json_sink, level=settings.log_level.upper())
    else:
        logger.add(
            sink=sys.stderr,
            level=settings.log_level.upper(),
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level:<8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - {message}",
        )


@app.command()
def run() -> None:
    settings = Settings()
    _setup_logger(settings)
    logger.debug("Settings loaded: {}", settings.model_dump())
    asyncio.run(run_application(settings))


@app.command()
def migrate() -> None:
    settings = Settings()
    _setup_logger(settings)
    logger.info("Applying pending migrations")
    up(settings.database_dsn)
    logger.info("Migrations applied")


@app.command()
def migrate_down() -> None:
    settings = Settings()
    _setup_logger(settings)
    logger.info("Rolling back last migration")
    down(settings.database_dsn)
    logger.info("Rollback complete")


@app.command()
def migrate_drop() -> None:
    settings = Settings()
    _setup_logger(settings)
    logger.info("Rolling back all migrations")
    drop(settings.database_dsn)
    logger.info("All migrations rolled back")


if __name__ == "__main__":
    app()
