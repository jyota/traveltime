from flask import Flask, jsonify, request
from flask_cors import CORS
from flask.json import JSONEncoder
from os import environ
from json import dumps, loads
from redis_wrapper import redis_connection
from jobs import get_optimum_time
from rq import Queue
from dateutil import parser
from pytz import timezone
from datetime import datetime
from input_validation import basicInputValidator
import googlemaps 

# ex. curl -H "Content-Type: application/json" -X POST -d '{"dest_to_orig_only": false, depart_start": "2017-06-14T08:00:00", "depart_end": "2017-06-14T10:00:00", "depart_loc": "16403 25th Ave SE, Bothell, WA 98012", "dest_loc": "2606 116th Ave NE, Bellevue, WA 98004", "min_mins_loc": 480, "max_mins_loc": 540, "traffic_model": "pessimistic"}' http://traveltime-jobservice.integrated.pro/v1/run_task


gmaps_timezone = googlemaps.Client(key='AIzaSyB8ZZq3WTIqc0n2e0FnYNJhnv4QFks5yb8')
gmaps_geocoding = googlemaps.Client(key='AIzaSyBRlAX7vk766IZQEd-2mCyqo05pLhLBgLw')

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
CORS(app)

@app.route("/v1/run_task", methods=['POST'])
def submit():
  request_details = request.get_json()

  try: 
    basic_validation_result = basicInputValidator.validate(request_details)
    assert basic_validation_result
  except AssertionError:
    return jsonify({'job_id': None, 'status': 'error_input_structure_validation'})

  q = Queue(connection=redis_connection)
  depart_loc = request_details['depart_loc']
  dest_loc = request_details['dest_loc']

  try: 
    depart_geo_info = gmaps_geocoding.geocode(depart_loc)
    request_timezone_info = gmaps_timezone.timezone((
      depart_geo_info[0]['geometry']['location']['lat'], 
      depart_geo_info[0]['geometry']['location']['lng']))
    assert request_timezone_info['status'] == 'OK'
  except:
    return jsonify({'job_id': None, 'status': 'api_error_timezonelookup'})

  time_grain = 15
  traffic_model = request_details['traffic_model']
  depart_start = timezone_to_utc(request_timezone_info['timeZoneId'], parser.parse(request_details['depart_start']))
  depart_end = timezone_to_utc(request_timezone_info['timeZoneId'], parser.parse(request_details['depart_end']))
  depart_span = depart_end - depart_start
  depart_diff_mins = depart_span.total_seconds() / 60
  orig_to_dest_only = request_details['orig_to_dest_only']

  if not orig_to_dest_only:
    min_mins_loc = request_details['min_mins_loc']
    max_mins_loc = request_details['max_mins_loc']
    diff_mins = max_mins_loc - min_mins_loc

    if not (depart_diff_mins + diff_mins) <= 480 or not depart_diff_mins >= 0 or not diff_mins >= 0:
      return jsonify({'job_id': None, 'status': 'error_time_span'})  
  else:
    min_mins_loc = 0
    max_mins_loc = 0
    if not depart_diff_mins <= 480 or not depart_diff_mins >= 0:
      return jsonify({'job_id': None, 'status': 'error_time_span'})  

  job = q.enqueue(get_optimum_time, 
	  depart_loc,
 	  dest_loc,
	  depart_start,
	  depart_end,
	  min_mins_loc, max_mins_loc,
	  time_grain, traffic_model, request_timezone_info,
    orig_to_dest_only)

  return jsonify({'job_id': job.get_id(), 'status': 'submitted_job'})

@app.route("/v1/status/<job_id>")
def job_status(job_id):
  q = Queue(connection=redis_connection)
  job = q.fetch_job(job_id)
  if job is None:
    response = {'status': 'unknown'}
  else:
    working_result = job.result
    if type(working_result) is dict and 'orig_to_dest' in working_result:
	    working_result['orig_to_dest'] = utc_to_timezone(working_result['requested']['tz_in']['timeZoneId'], 
							     working_result['orig_to_dest'])
            if 'dest_to_orig' in working_result:
	         working_result['dest_to_orig'] = utc_to_timezone(working_result['requested']['tz_in']['timeZoneId'], 
		    					          working_result['dest_to_orig'])
	    working_result['requested']['min_leave_in'] = utc_to_timezone(working_result['requested']['tz_in']['timeZoneId'],
									  working_result['requested']['min_leave_in'])
	    working_result['requested']['max_leave_in'] = utc_to_timezone(working_result['requested']['tz_in']['timeZoneId'],
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



