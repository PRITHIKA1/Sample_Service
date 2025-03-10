from fastapi import FastAPI
from pymongo import MongoClient
from src.config import MONGO_URI, MONGO_DB
import logging
from opentelemetry.instrumentation.pymongo import PymongoInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

app = FastAPI()
FastAPIInstrumentor.instrument_app(app)

# Enable auto-instrumentation for PyMongo
PymongoInstrumentor().instrument()

# Enable logging instrumentation to capture all logs as traces
LoggingInstrumentor().instrument(set_logging_format=True)

# Enable detailed logging for errors
logging.basicConfig(level=logging.ERROR)

# For Generating Timeout Error
# try:
#     client = MongoClient(MONGO_URI)
#     db = client[MONGO_DB]
# except Exception as e:
#     logging.error("MongoDB Connection Error", exc_info=True)

client = MongoClient(
    MONGO_URI,
    tls=True,  # Enable SSL/TLS
    tlsAllowInvalidCertificates=True  # Bypass certificate verification if necessary
)

db = client[MONGO_DB]
