import time
from functools import wraps
from loguru import logger
from opentelemetry import trace
from src.core.metrics import DB_QUERY_DURATION_SECONDS
import src.adapters.repository.errors as adapter_errors

EXPECTED_EXCEPTIONS = (
    adapter_errors.EventNotFoundError,
    adapter_errors.EventAlreadyExistsError,
    adapter_errors.ParticipantNotFoundError,
    adapter_errors.ParticipantAlreadyExistsError,
    adapter_errors.RepositoryError,
)
tracer = trace.get_tracer(__name__)


def trace_db_operation(service: str, operation: str, table: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            with tracer.start_as_current_span(
                f"db.{operation.lower()}.{table}"
            ) as span:
                span.set_attribute("db.system", "postgresql")
                span.set_attribute("db.operation", operation)
                span.set_attribute("db.sql.table", table)

                start = time.perf_counter()

                try:
                    result = await func(*args, **kwargs)

                    duration = time.perf_counter() - start

                    DB_QUERY_DURATION_SECONDS.labels(
                        service=service,
                        operation=operation,
                        table=table
                    ).observe(duration)

                    logger.debug(
                        "db_query_success",
                        operation=operation,
                        table=table,
                        duration_ms=round(duration * 1000, 2),
                    )

                    return result
                except Exception as e:
                    duration = time.perf_counter() - start

                    span.record_exception(e)
                    span.set_status(trace.StatusCode.ERROR, str(e))

                    if not isinstance(e, EXPECTED_EXCEPTIONS):
                        logger.error(
                            "db_query_failed",
                            operation=operation,
                            table=table,
                            duration_ms=round(duration * 1000, 2),
                            error_type=type(e).__name__,
                        )
                    else:
                        logger.debug(
                            "db_query_business_error",
                            operation=operation,
                            table=table,
                            error_type=type(e).__name__,
                        )

                    raise
        return wrapper
    return decorator
