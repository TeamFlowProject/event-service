from loguru import logger
from functools import wraps
from opentelemetry import trace
from src.core.metrics import BUSINESS_OPERATION_ERRORS_TOTAL, BUSINESS_OPERATIONS_TOTAL

tracer = trace.get_tracer(__name__)


def trace_business_logic(service: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            with tracer.start_as_current_span(f"{service}.{func.__name__}") as span:
                try:
                    result = await func(*args, **kwargs)

                    BUSINESS_OPERATIONS_TOTAL.labels(
                        service=service,
                        operation=func.__name__,
                        status="success",
                    ).inc()

                    return result

                except Exception as e:
                    BUSINESS_OPERATIONS_TOTAL.labels(
                        service=service,
                        operation=func.__name__,
                        status="error",
                    ).inc()
                    BUSINESS_OPERATION_ERRORS_TOTAL.labels(
                        service=service,
                        operation=func.__name__,
                        error_type=type(e).__name__
                    ).inc()

                    span.record_exception(e)
                    span.set_status(trace.StatusCode.ERROR, str(e))

                    logger.exception(
                        f"service_{func.__name__}_failed",
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    raise
        return wrapper
    return decorator
