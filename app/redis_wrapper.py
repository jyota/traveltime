import redis
from os import environ

redis_connection = redis.from_url(environ.get('REDIS_URL', 'redis://'))

