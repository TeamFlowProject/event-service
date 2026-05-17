from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response

# HTTP metrics for middleware
HTTP_REQUESTS_TOTAL = Counter(
    name="http_requests_total",
    documentation="Total number of HTTP requests",
    labelnames=["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    name="http_request_duration_seconds",
    documentation="Время обработки HTTP запроса",
    labelnames=["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# Business metrics
BUSINESS_OPERATIONS_TOTAL = Counter(
    name="business_operations_total",
    documentation="Количество бизнес-операций",
    labelnames=["service", "operation", "status"],  # status: success / error
)

BUSINESS_OPERATION_ERRORS_TOTAL = Counter(
    name="business_operation_errors_total",
    documentation="Количество ошибок бизнес-операций",
    labelnames=["service", "operation", "error_type"],
)
# Infrastructure metrics
DB_QUERY_DURATION_SECONDS = Histogram(
    name="db_query_duration_seconds",
    documentation="Время выполнения запросов к базе данных",
    labelnames=["service", "operation", "table"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
)

KAFKA_MESSAGES_SENT_TOTAL = Counter(
    name="kafka_messages_sent_total",
    documentation="Количество отправленных сообщений в Kafka",
    labelnames=["service", "topic", "status"],  # status: success / error
)


async def metrics_endpoint(request: Request) -> Response:
    """
    GET /metrics
    Prometeus pulls metrics every 15 seconds.

    Returns:
        Response: Prometheus metrics in text format
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
