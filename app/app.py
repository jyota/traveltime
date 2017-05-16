from flask import Flask, jsonify, request
from flask.json import JSONEncoder
from os import environ
from json import dumps, loads
from redis_wrapper import redis_connection
from jobs import get_optimum_time
from rq import Queue
from dateutil import parser
from pytz import timezone
from datetime import datetime
# ex. curl -H "Content-Type: application/json" -X POST -d '{"depart_start": "2017-03-02T08:00:00", "depart_end": "2017-03-02T10:00:00", "depart_loc": "Shinjuku, Tokyo", "dest_loc": "Ueno Park, Tokyo", "min_mins_loc": 480, "max_mins_loc": 540, "traffic_model": "pessimistic", "timezone": "Japan"}' http://localhost/v1/run_task

class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        try:
            if isinstance(obj, datetime):
		obj = obj.strftime('%Y-%m-%dT%H:%M:%S')
		return obj
	    iterable = iter(obj)      
        except TypeError:
            pass
        else:
            return list(iterable)
        return JSONEncoder.default(self, obj)


def timezone_to_utc(timezone_in, datetime_in):
  from_timezone = timezone(timezone_in)
  to_timezone = timezone('UTC')
  delta_to_timezone = from_timezone.localize(datetime_in) - to_timezone.localize(datetime_in)
  return datetime_in + delta_to_timezone

def utc_to_timezone(timezone_in, datetime_in):
  from_timezone = timezone('UTC')
  to_timezone = timezone(timezone_in)
  delta_to_timezone = from_timezone.localize(datetime_in) - to_timezone.localize(datetime_in)
  return datetime_in + delta_to_timezone


app = Flask(__name__)
app.json_encoder = CustomJSONEncoder
app.debug = True


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
	time_grain, traffic_model, request_timezone)
  return job.get_id()

@app.route("/v1/status/<job_id>")
def job_status(job_id):
  q = Queue(connection=redis_connection)
  job = q.fetch_job(job_id)
  if job is None:
    response = {'status': 'unknown'}
  else:
    working_result = job.result
    if type(working_result) is dict and 'orig_to_dest' in working_result:
	    working_result['orig_to_dest'] = utc_to_timezone(working_result['requested']['tz_in'], 
							     working_result['orig_to_dest'])
	    working_result['dest_to_orig'] = utc_to_timezone(working_result['requested']['tz_in'], 
							     working_result['dest_to_orig'])
	    working_result['requested']['min_leave_in'] = utc_to_timezone(working_result['requested']['tz_in'],
									  working_result['requested']['min_leave_in'])
	    working_result['requested']['max_leave_in'] = utc_to_timezone(working_result['requested']['tz_in'],
									  working_result['requested']['max_leave_in'])

    response = {
      'status': (job.meta['status']
                 if 'status' in job.meta
                 else 'unknown'),
      'result': working_result
    }
    if job.is_failed:
      response['message'] = job.exc_info.strip().split('\n')[-1]

    return jsonify(response)



