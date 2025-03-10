import ssl

import redis
from src.config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD
from opentelemetry.instrumentation.redis import RedisInstrumentor

# Enable Redis instrumentation
RedisInstrumentor().instrument()

# cache = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, decode_responses=True)


cache = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    ssl=True,  # ✅ Required for Azure Redis
    ssl_cert_reqs=ssl.CERT_NONE,  # ✅ Bypass SSL verification
    decode_responses=True
)