from config.env import ENVIRONMENT, REDIS_HOST, REDIS_PORT, REDIS_USERNAME, REDIS_PASSWORD, REDIS_DATABASE
import redis

if ENVIRONMENT == "production":
    redis_db = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DATABASE,
        username=REDIS_USERNAME,
        password=REDIS_PASSWORD,
        ssl=True,
        ssl_cert_reqs=None,
        decode_responses=False,
    )
else:
    redis_db = redis.Redis(
        host=REDIS_HOST, 
        port= REDIS_PORT,
        db=REDIS_DATABASE,
        username=REDIS_USERNAME,
        password=REDIS_PASSWORD,
        decode_responses=True
    )