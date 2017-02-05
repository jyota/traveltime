from flask import Flask
from celery_wrapper import make_celery

flask_app = Flask(__name__)
flask_app.config.update(
   CELERY_BROKER_URL='amqp://localhost',
   CELERY_RESULT_BACKEND='rpc://'
)

celery_wrapper = make_celery(flask_app)

@celery_wrapper.task()
def returner():
  return 'hewitt!'

@flask_app.route("/")
def initial():
  str_val = returner.delay()
  return str_val.wait() 

if __name__ == "__main__":
  flask_app.run(host='0.0.0.0', debug=True, port=80)

