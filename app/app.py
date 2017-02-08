from flask import Flask, jsonify
from os import environ
from json import dumps
from redis_wrapper import redis_connection
from jobs import get_it
from rq import Queue

app = Flask(__name__)

@app.route("/v1/run_task")
def submit():
  q = Queue(connection=redis_connection)
  job = q.enqueue(get_it, 5)
  return job.get_id()

@app.route("/v1/status/<job_id>")
def job_status(job_id):
  q = Queue(connection=redis_connection)
  job = q.fetch_job(job_id)
  if job is None:
    response = {'status': 'unknown'}
  else:
    response = {
      'status': job.get_status(),
      'result': job.result
    }
    if job.is_failed:
      response['message'] = job.exc_info.strip().split('\n')[-1]

    return jsonify(response)



