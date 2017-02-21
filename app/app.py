from flask import Flask, jsonify
from os import environ
from json import dumps
from redis_wrapper import redis_connection
from jobs import get_optimum_time
from rq import Queue
from datetime import datetime

app = Flask(__name__)

@app.route("/v1/run_task")
def submit():
  q = Queue(connection=redis_connection)
  job = q.enqueue(get_optimum_time, 
	"16403 25th Ave SE, Bothell, WA 98012",
	"2606 116th Ave NE, Bellevue, WA 98004",
	datetime(2017, 2, 21, 14, 30),
	datetime(2017, 2, 21, 16, 00),
	60 * 8, 60 * 9,
	15, "best_guess")
  return job.get_id()

@app.route("/v1/status/<job_id>")
def job_status(job_id):
  q = Queue(connection=redis_connection)
  job = q.fetch_job(job_id)
  if job is None:
    response = {'status': 'unknown'}
  else:
    response = {
      'status': job.meta['status'],
      'result': job.result
    }
    if job.is_failed:
      response['message'] = job.exc_info.strip().split('\n')[-1]

    return jsonify(response)



