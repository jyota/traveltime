from rq import Connection, Worker
from redis_wrapper import redis_connection 
from jobs import get_optimum_time

with Connection(redis_connection):
  qs = ['default']
  w = Worker(qs)
  w.work()

