from opentelemetry import trace
from opentelemetry.sdk.trace import TraceProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME


def setup_tracing(
        service_name: str,
        otlp_endpoint: str = "http://localhost:4317",
) -> None:
    """
    OpenTelemetry tracing initialization and Jaeger export connection.

    Args:
        service_name: The name of the service that will  be displayed in Jaeger
        otlp_endpoint: jgRPC address of Jaeger
    """
    resource = Resource.create({SERVICE_NAME: service_name})

    exporter = OTLPSpanExporter(
        endpoint=otlp_endpoint,
        insecure=True,  # !!! no TLS for local development
    )

    provider = TraceProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))

    # Global registration for trace.get_tracer() to return this provider everywhere
    trace.set_tracer_provider(provider)
