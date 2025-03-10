from fastapi import Request
from fastapi.responses import JSONResponse
from opentelemetry import trace
from opentelemetry.trace.status import Status, StatusCode
import logging

tracer = trace.get_tracer(__name__)  # Get the OpenTelemetry tracer


async def opentelemetry_middleware(request: Request, call_next):
    with tracer.start_as_current_span(f"Request: {request.url.path}") as span:
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logging.error(f"Unhandled error: {e}")

            # ✅ Automatically capture the exception in OpenTelemetry traces
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR))

            return JSONResponse(
                content={"error": "Internal Server Error"},
                status_code=500
            )
