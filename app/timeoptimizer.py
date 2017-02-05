import googlemaps
from datetime import datetime, timedelta

gmaps = googlemaps.Client(key='AIzaSyBcHydWjoBKKQ9hFciBHuxu2EAv36mIjUI')

class DirectionTimeOptimizer:
    def __init__(self, origin, destination, 
                 min_time_to_leave, max_time_to_leave, 
                 min_time_at_dest, max_time_at_dest,
                 search_granularity_mins=15, traffic_model="best_guess"):
        self.origin = origin
        self.destination = destination
        self.min_time_to_leave = self.round_closest_mins(min_time_to_leave)
        self.max_time_to_leave = self.round_closest_mins(max_time_to_leave)
        self.min_time_at_dest = self.round_closest(min_time_at_dest)
        self.max_time_at_dest = self.round_closest(max_time_at_dest)
        self.search_granularity_mins = search_granularity_mins
        self.time_to_leave_segments = int((((self.max_time_to_leave - self.min_time_to_leave).total_seconds() / 60) / self.search_granularity_mins)) + 1
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
            result = self.get_duration_from_result(
                gmaps.directions(self.origin,
                                 self.destination,
                                 mode="driving",
                                 traffic_model=self.traffic_model,                                         
                                 departure_time=time_to_leave))
        
            if result is not None:
                self.origin_leave_time_lookup[time_to_leave] = {
                    'orig_to_dest_time': result}

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
                result = self.get_duration_from_result(
                    gmaps.directions(self.destination,
                                     self.origin,
                                     mode="driving",
                                     traffic_model=self.traffic_model,                                         
                                     departure_time=dest_leave_time))
                if 'dest_return_time_lookup' not in self.origin_leave_time_lookup[leave_time] and result is not None:
                    self.origin_leave_time_lookup[leave_time]['dest_return_time_lookup'] = {}
                    self.origin_leave_time_lookup[leave_time]['dest_return_time_lookup'][dest_leave_time] = result
                elif 'dest_return_time_lookup' in self.origin_leave_time_lookup[leave_time] and result is not None:
                    self.origin_leave_time_lookup[leave_time]['dest_return_time_lookup'][dest_leave_time] = result

        return True


    def determine_optimum_times(self):
        try:
            self.calculate_possible_times_to_leave()
            self.calculate_possible_times_to_return()

            min_combination = {
                'orig_to_dest': None,
                'dest_to_orig': None,
                'status': 'Success'
            }

            min_seen = 10000000
            for timestamp, item in self.origin_leave_time_lookup.iteritems():
                for sub_ts, sub_item in item['dest_return_time_lookup'].iteritems():
                    if (item['orig_to_dest_time'] + sub_item) < min_seen:
                        min_seen = item['orig_to_dest_time'] + sub_item
                        min_combination['orig_to_dest'] = timestamp
                        min_combination['dest_to_orig'] = sub_ts

            min_combination['est_travel_time_mins'] = min_seen
            return min_combination
        except:
            return {'status': 'Fail'}


my_optimizer = DirectionTimeOptimizer("16403 25th Ave SE, Bothell, WA 98012",
                                      "2606 116th Ave NE, Bellevue, WA 98004",
                                      datetime(2017, 1, 15, 7, 55), 
                                      datetime(2017, 1, 15, 9, 55),
                                      60 * 7, 60 * 8)


result = my_optimizer.determine_optimum_times()

