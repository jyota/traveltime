from os import environ
from time import sleep
from celery import Celery

CELERY_BROKER_URL = environ.get('CELERY_BROKER_URL','amqp://localhost'),
CELERY_RESULT_BACKEND = environ.get('CELERY_RESULT_BACKEND','rpc://')
CELERY_IGNORE_RESULT = False

celery= Celery('jobs',
                broker=CELERY_BROKER_URL,
                backend=CELERY_RESULT_BACKEND,
		task_ignore_result = CELERY_IGNORE_RESULT)

@celery.task(name='job.calculate')
def calculate_traveltime(job_data):
  sleep(5)    
  return {'done': True}
 
