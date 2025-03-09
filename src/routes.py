from opentelemetry import trace

from fastapi import APIRouter, HTTPException, FastAPI
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
import sys
from opentelemetry.instrumentation.logging import LoggingInstrumentor
import httpx
from pymongo import MongoClient
import redis
import logging

app = FastAPI()
tracer = trace.get_tracer(__name__)
logging.basicConfig(level=logging.INFO)

# Configure logging
LoggingInstrumentor().instrument()
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

RequestsInstrumentor().instrument()
HTTPXClientInstrumentor().instrument()

router = APIRouter()

# MongoDB Connection
try:
    mongo_client = MongoClient("mongodb://loalhost:27017/")
    db = mongo_client["mydatabase"]
except Exception as e:
    raise Exception(f"MongoDB Connection Error: {str(e)}")

# Redis Connection
try:
    cache = redis.Redis(host="localhost", port=6379, decode_responses=True)
except Exception as e:
    raise Exception(f"Redis Connection Error: {str(e)}")


# API-1: Fetch data from MongoDB
@router.get("/mongo-data")
def get_mongo_data():
    try:
        data = list(db["collection"].find({}, {"_id": 0}))
        return {"mongo_data": data}
    except Exception as e:
        logging.error(f"Error in /mongo-data: {e}")
        raise HTTPException(status_code=500, detail=f"MongoDB Fetch Error: {str(e)}")


# API-2: Fetch data from Cache
@router.get("/cache-data")
def get_cache_data():
    try:
        data = cache.get("cached_key")
        if data is None:
            raise HTTPException(status_code=404, detail="Cache key not found")
        return {"cache_data": data}
    except Exception as e:
        logging.error(f"Error in /cache-data: {e}")
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
