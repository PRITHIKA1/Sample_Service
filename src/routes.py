import logging
import sys

import httpx
from bson import ObjectId
from fastapi import APIRouter, HTTPException, FastAPI
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from opentelemetry.trace import Status, StatusCode

from src.cache import cache
from src.database import db

app = FastAPI()
tracer = trace.get_tracer(__name__)
logging.basicConfig(level=logging.INFO)

# Configure logging
LoggingInstrumentor().instrument()
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

RequestsInstrumentor().instrument()
HTTPXClientInstrumentor().instrument()
FastAPIInstrumentor.instrument_app(app)

router = APIRouter()


# API-1: Fetch data from MongoDB
@router.get("/mongo-data/{idd}")
async def get_mongo_data(idd: str):
    with tracer.start_as_current_span("MongoDB Query") as span:
        try:
            collection = db["failed_hotel_batches"]  # Replace with your actual collection name

            query = {"_id": ObjectId(idd)} if ObjectId.is_valid(idd) else {"_id": idd}
            data = collection.find_one(query)

            if data:
                data["_id"] = str(data["_id"])  # Convert ObjectId to string
                return {"success": True, "data": data}
            else:
                return {"success": False, "message": "Data not found"}

        except Exception as e:
            logging.error(f"Error in /mongo-data: {e}")
            span.record_exception(e)  # ✅ Explicitly capture MongoDB errors
            span.set_status(Status(StatusCode.ERROR))
            raise HTTPException(status_code=500, detail=f"MongoDB Fetch Error: {str(e)}")


# @router.get("/mongo-data")
# def get_mongo_data():
#     try:
#         data = list(db["failed_hotel_batches"].find({}, {"_id": "e0e80557-aec6-41ed-b73f-4a0dc127d421"}))
#         return {"mongo_data": data}
#     except Exception as e:
#         logging.error(f"Error in /mongo-data: {e}")
#         raise HTTPException(status_code=500, detail=f"MongoDB Fetch Error: {str(e)}")


# API-2: Fetch data from Cache
# @router.get("/cache-data")
# def get_cache_data():
#     try:
#         data = cache.get("HYD-STV")
#         if data is None:
#             raise HTTPException(status_code=404, detail="Cache key not found")
#         return {"cache_data": data}
#     except Exception as e:
#         logging.error(f"Error in /cache-data: {e}")
#         raise HTTPException(status_code=500, detail=f"Cache Fetch Error: {str(e)}")

# PII Masking Function

# Initialize PII Detector
analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()


def mask_pii(text):
    """Detect and mask PII in text using Presidio."""
    if not text:
        return text

    # Detect PII entities
    results = analyzer.analyze(text=text, entities=[], language="en")

    # Mask detected PII
    anonymized_text = anonymizer.anonymize(text=text, analyzer_results=results)

    return anonymized_text.text


@router.get("/cache-data")
def get_cache_data():
    with tracer.start_as_current_span("Redis Query") as span:
        try:
            data = cache.get("Hello")

            if data is None:
                span.set_status(Status(StatusCode.ERROR))
                span.add_event("Cache key not found")
                raise HTTPException(status_code=404, detail="Cache key not found")

            span.add_event("Cache hit")
            masked_data = mask_pii(data)
            span.set_attribute("response_body", masked_data)
            return {"cache_data": data}

        except Exception as e:
            logging.error(f"Error in /cache-data: {e}")

            # ✅ Capture exception in OpenTelemetry
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR))

            raise HTTPException(status_code=500, detail=f"Cache Fetch Error: {str(e)}")


# API-3: Fetch data from both MongoDB and Cache
@router.get("/mongo-cache-data")
async def get_mongo_cache_data():
    try:
        mongo_data = list(db["collection"].find({}, {"_id": 0}))
        cache_data = cache.get("cached_key")
        async with httpx.AsyncClient(timeout=5) as client:  # 5-second timeout
            response = await client.get("http://0.0.0.0:8001/external-api")
            response.raise_for_status()  # Raises an error for non-200 responses
        if cache_data is None:
            cache_data = "No cache data found"
        return {"mongo_data": mongo_data, "cache_data": cache_data, "api_data": response}
    except Exception as e:
        logging.error(f"Error in /mongo-cache-data: {e}")
        raise HTTPException(status_code=500, detail=f"MongoDB/Cache Fetch ZxError: {str(e)}")


# API-4: Fetch data from an external API
@router.get("/external-api")
async def get_external_api():
    try:
        async with httpx.AsyncClient(timeout=5) as client:  # 5-second timeout
            response = await client.get("http://0.0.0.0:8001/external-apiiii")
            response.raise_for_status()  # Raises an error for non-200 responses
            return response.json()
    except httpx.HTTPStatusError as http_err:
        logging.error(f"Error in /external-api: {http_err}")
        raise HTTPException(status_code=response.status_code, detail=f"External API Error: {str(http_err)}")
    except httpx.RequestError as req_err:
        logging.error(f"Error in /external-api: {req_err}")
        raise HTTPException(status_code=400, detail=f"External API Request Failed: {str(req_err)}")
    except Exception as e:
        logging.error(f"Error in /external-api: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected Error: {str(e)}")
