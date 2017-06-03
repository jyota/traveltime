from cerberus import Validator
from pytz import all_timezones


input_schema = {'traffic_model': {'type': 'string',
                                  'required': True,
                                  'allowed': ['pessimistic', 'optimistic', 'best_guess']},
                'max_mins_loc': {'type': 'integer',
                                 'required': True},
                'min_mins_loc': {'type': 'integer',
                                 'required': True},
                'depart_loc': {'type':  'string',
                               'required': True},
                'dest_loc': {'type': 'string',
                             'required': True},
                'depart_start': {'type': 'string',
                                 'required': True,
                                 'minlength': 13,
                                 'maxlength': 19},
                'depart_end': {'type': 'string',
                                 'required': True,
                                 'minlength': 13,
                                 'maxlength': 19}}

basicInputValidator = Validator(input_schema)
