import googlemaps
from datetime import datetime, timedelta
from rq.decorators import job
from os import environ
from time import sleep
from redis_wrapper import redis_connection
from rq import get_current_job

gmaps = googlemaps.Client(key='AIzaSyCKKLTC8A5HMzXKtcPbOHhsfCkbj16n98Y')

@job('default', connection=redis_connection)
def get_optimum_time(orig_in, dest_in, min_leave_in, max_leave_in, min_dest_in, max_dest_in, granularity_in, traffic_model_in, tz_in, orig_to_dest_only_in):
	class DirectionTimeOptimizer:
	    def __init__(self, origin, destination, 
			 min_time_to_leave, max_time_to_leave, 
			 min_time_at_dest, max_time_at_dest,
			 orig_to_dest_only, 
			 search_granularity_mins=15, traffic_model="best_guess"):
		self.origin = origin
		self.orig_to_dest_only = orig_to_dest_only
		self.destination = destination
		self.min_time_to_leave = self.round_closest_mins(min_time_to_leave)
		self.max_time_to_leave = self.round_closest_mins(max_time_to_leave)
		self.search_granularity_mins = int(search_granularity_mins)
		self.time_to_leave_segments = int((((self.max_time_to_leave - self.min_time_to_leave).total_seconds() / 60) / self.search_granularity_mins)) + 1
		if not orig_to_dest_only:
			self.min_time_at_dest = self.round_closest(min_time_at_dest)
			self.max_time_at_dest = self.round_closest(max_time_at_dest)
			self.time_at_dest_segments = int((max_time_at_dest - min_time_at_dest) / search_granularity_mins) + 1
		self.traffic_model = traffic_model
		self.origin_leave_time_lookup = {}
	    
	    def round_closest(self, value, quantization=15):
		return int(quantization * round(value / float(quantization)))
	    
	    def round_closest_mins(self, time_value, quantization=15):
		return (time_value + 
			timedelta(minutes=self.round_closest(time_value.minute) - time_value.minute))
	    
	    def get_duration_from_result(self, result):
		if (not len(result) > 0 or 'legs' not in result[0] or 
		    not len(result[0]['legs']) > 0 or 'duration_in_traffic' not in result[0]['legs'][0]):
		    return None
		else:
		    return result[0]['legs'][0]['duration_in_traffic']['value'] / 60.0
		
	    def calculate_possible_times_to_leave(self):
		min_set = [self.min_time_to_leave + timedelta(minutes=i*self.search_granularity_mins)
			   for i in xrange(0, self.time_to_leave_segments)]
		
		for time_to_leave in min_set:
			gmaps_result = gmaps.directions(self.origin,
					 self.destination,
					 mode="driving",
					 traffic_model=self.traffic_model,                                         
					 departure_time=time_to_leave)
			result = self.get_duration_from_result(gmaps_result)
			if result is not None:
				self.origin_leave_time_lookup[time_to_leave] = {
				'orig_to_dest_time': result,
				'summary_name': gmaps_result[0]['summary']}

		if not self.origin_leave_time_lookup == {}:
		    return True
		else:
		    return False
		    
	    def calculate_possible_times_to_return(self):
		if self.origin_leave_time_lookup == {}:
		    return False
		
		for leave_time in self.origin_leave_time_lookup.keys():
		    time_set = [leave_time + timedelta(minutes=(i*self.search_granularity_mins) + 
						       self.round_closest(int(self.origin_leave_time_lookup[leave_time]['orig_to_dest_time'])) + 
						       self.min_time_at_dest)
				 for i in xrange(0, self.time_at_dest_segments)]

		    for dest_leave_time in time_set:
		    	gmaps_result = gmaps.directions(self.destination,
					     self.origin,
					     mode="driving",
					     traffic_model=self.traffic_model,                                         
					     departure_time=dest_leave_time)
		    	result = self.get_duration_from_result(gmaps_result)
		    	if 'dest_return_time_lookup' not in self.origin_leave_time_lookup[leave_time] and result is not None:
		    		self.origin_leave_time_lookup[leave_time]['dest_return_time_lookup'] = {}
		    		self.origin_leave_time_lookup[leave_time]['dest_return_time_lookup'][dest_leave_time] = {
		    		  'dest_to_orig_time': result,
		    		  'summary_name': gmaps_result[0]['summary']}
		    	elif 'dest_return_time_lookup' in self.origin_leave_time_lookup[leave_time] and result is not None:
		    		self.origin_leave_time_lookup[leave_time]['dest_return_time_lookup'][dest_leave_time] = {
		    		  'dest_to_orig_time': result,
		    		  'summary_name': gmaps_result[0]['summary']}

		return True


	    def determine_optimum_times_both_dirs(self):
		    min_combination = {
			'orig_to_dest': None,
			'dest_to_orig': None,
			'orig_to_dest_summary': None,
			'dest_to_orig_summary': None,
			'status': 'Success'
		    }

		    min_seen = 10000000
		    for timestamp, item in self.origin_leave_time_lookup.iteritems():
		    	for sub_ts, sub_item in item['dest_return_time_lookup'].iteritems():
		    		if (item['orig_to_dest_time'] + sub_item['dest_to_orig_time']) < min_seen:
		    			min_seen = item['orig_to_dest_time'] + sub_item['dest_to_orig_time']
		    			min_combination['orig_to_dest'] = timestamp
		    			min_combination['dest_to_orig'] = sub_ts
		    			min_combination['orig_to_dest_time'] = item['orig_to_dest_time']
		    			min_combination['dest_to_orig_time'] = sub_item['dest_to_orig_time']
		    			min_combination['orig_to_dest_summary'] = item['summary_name']
		    			min_combination['dest_to_orig_summary'] = sub_item['summary_name']

		    return min_combination


	    def determine_optimum_times_one_dir(self):
		    min_combination = {
			'orig_to_dest': None,
			'orig_to_dest_summary': None,
			'status': 'Success'
		    }

		    min_seen = 10000000
		    for timestamp, item in self.origin_leave_time_lookup.iteritems():
	    		if item['orig_to_dest_time'] < min_seen:
	    			min_seen = item['orig_to_dest_time']
	    			min_combination['orig_to_dest'] = timestamp
	    			min_combination['orig_to_dest_time'] = item['orig_to_dest_time']
	    			min_combination['orig_to_dest_summary'] = item['summary_name']

		    return min_combination



	job = get_current_job()
	job.meta['status'] = 'create'
	job.save()
	my_optimizer = DirectionTimeOptimizer(orig_in, dest_in, min_leave_in, max_leave_in, 
					      min_dest_in, max_dest_in, orig_to_dest_only_in, granularity_in, traffic_model_in)
	job.meta['status'] = 'created'
	job.save()

	try:
	  my_optimizer.calculate_possible_times_to_leave()
	  job.meta['status'] = 'times_to_leave_done'
	  job.save()
	  if not orig_to_dest_only_in:
	    my_optimizer.calculate_possible_times_to_return()
	    job.meta['status'] = 'times_to_return_done'
	    job.save()
	except googlemaps.exceptions.ApiError as e:
		if 'departure_time is in the past' in str(e):
			job.meta['status'] = 'api_error_departure_in_the_past'
			job.save()
			return None
		else:
			job.meta['status'] = 'api_error_unknown'
			job.save()
			return None

	if not orig_to_dest_only_in:
	  result = my_optimizer.determine_optimum_times_both_dirs()
	else:
	  result = my_optimizer.determine_optimum_times_one_dir()
	
	job.meta['status'] = 'complete'
	job.save()
	result['requested'] = ({'orig_to_dest_only': orig_to_dest_only_in, 'orig_in': orig_in, 'dest_in': dest_in, 'min_leave_in': min_leave_in,
				'max_leave_in': max_leave_in, 'min_dest_in': min_dest_in, 'max_dest_in': max_dest_in,
				'granularity_in': granularity_in, 'traffic_model_in': traffic_model_in, 'tz_in': tz_in}
				if not orig_to_dest_only_in
				else {'orig_to_dest_only': orig_to_dest_only_in, 'orig_in': orig_in, 'dest_in': dest_in, 'min_leave_in': min_leave_in,
				'max_leave_in': max_leave_in, 'granularity_in': granularity_in, 'traffic_model_in': traffic_model_in, 'tz_in': tz_in})
	return result

