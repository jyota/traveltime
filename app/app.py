from flask import Flask, jsonify, request
from os import environ
from json import dumps, loads
from redis_wrapper import redis_connection
from jobs import get_optimum_time
from rq import Queue
from dateutil import parser
from pytz import timezone
# ex. curl -H "Content-Type: application/json" -X POST -d '{"depart_start": "2017-03-02 08:00:00", "depart_end": "2017-03-02 10:00:00", "depart_loc": "Shinjuku, Tokyo", "dest_loc": "Ueno Park, Tokyo", "min_mins_loc": 480, "max_mins_loc": 540, "traffic_model": "pessimistic", "timezone": "Japan"}' http://localhost/v1/run_task

app = Flask(__name__)
app.debug = True

def timezone_to_utc(timezone_in, datetime_in):
  from_timezone = timezone(timezone_in)
  to_timezone = timezone('UTC')
  delta_to_timezone = from_timezone.localize(datetime_in) - to_timezone.localize(datetime_in)
  return datetime_in + delta_to_timezone

@app.route("/v1/run_task", methods=['POST'])
def submit():
  request_details = request.get_json()

  q = Queue(connection=redis_connection)
  depart_loc = request_details['depart_loc']
  dest_loc = request_details['dest_loc']
  min_mins_loc = request_details['min_mins_loc']
  max_mins_loc = request_details['max_mins_loc']
  time_grain = 15
  traffic_model = request_details['traffic_model']
  request_timezone = request_details['timezone']
  depart_start = timezone_to_utc(request_timezone, parser.parse(request_details['depart_start']))
  depart_end = timezone_to_utc(request_timezone, parser.parse(request_details['depart_end']))

  job = q.enqueue(get_optimum_time, 
	depart_loc,
 	dest_loc,
	depart_start,
	depart_end,
	min_mins_loc, max_mins_loc,
	time_grain, traffic_model)
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



