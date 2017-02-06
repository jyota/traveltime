from os import environ
from celery import Celery

CELERY_BROKER_URL = environ.get('CELERY_BROKER_URL', 'amqp://localhost')
CELERY_RESULT_BACKEND = environ.get('CELERY_RESULT_BACKEND', 'rpc://')
CELERY_IGNORE_RESULT = False

celery = Celery('jobs', 
		backend = CELERY_RESULT_BACKEND,
		broker = CELERY_BROKER_URL,
		task_ignore_result = CELERY_IGNORE_RESULT)
