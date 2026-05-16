import time
import uuid

from loguru import logger
from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.core.metrics import HTTP_REQUESTS_TOTAL, HTTP_REQUEST_DURATION_SECONDS


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Middleware to observe all the requests.
    """

    SKIP_PATHS = {"/metrics", "/health", "/readiness"}

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        request_id = str(uuid.uuid4())
        start_time = time.perf_counter()

        current_span = trace.get_current_span()
        current_span.set_attribute("http.request_id", request_id)

        bound_logger = logger.bind(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        bound_logger.info("request_started")

        # the request
        response = await call_next(request)
        duration = time.perf_counter() - start_time

        # path normalization
        endpoint = self._normalize_path(request.url.path)

        HTTP_REQUESTS_TOTAL.labels(
            method=request.method,
            endpoint=endpoint,
            status_code=str(response.status_code),
        ).inc()

        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=request.method,
            endpoint=endpoint,
        ).observe(duration)

        bound_logger.info(
            "request_finished",
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2),
        )

        return response

    def _normalize_path(self, path: str) -> str:
        """
        Replace UUID segment to {id} to prevent broken time series in metrics

        /api/v1/events/550e8400-e29b-41d4-a716  ->  /api/v1/events/{id}
        /api/v1/events  ->  /api/v1/events
        """
        import re
        uuid_pattern = re.compile(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            re.IGNORECASE,
        )
        return uuid_pattern.sub("{id}", path)
