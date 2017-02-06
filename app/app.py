from flask import Flask
from worker import celery
from celery.result import AsyncResult
import celery.states as states
from os import environ
from json import dumps

flask_app = Flask(__name__)

@flask_app.route("/v1/jobs/submit")
def submit():
  task = celery.send_task('job.calculate', args=['nothing'], kwargs=[])
  return  task.id

@flask_app.route("/v1/jobs/get/<string:id>")
def get_job(id):
  result = celery.AsyncResult(id)
  if result.state == states.PENDING:
    return result.state
  else:
    return dumps(result.result)

if __name__ == "__main__":
  flask_app.run(debug=environ.get('DEBUG', True), 
		host=environ.get('HOST', '0.0.0.0'),
		port=int(environ.get('PORT', 5000)))


