'''
Handles communication with a database or memory cache
'''
import time

EVENT_TYPES = [
    'ADD-CL',  # add chlorine (gals)
    'ADD-ACID',  # add acid (gals)
    'ADD-ALGAECIDE',  # add algaecide (liters)
    'SWIM',  # swim load (num people)
    'BACKWASH',  # backwash filter
    'CLEAN-FILTER',  # clean filter
]

READING_TYPES = [
    'FC',  # free chlorine (ppm)
    'TC',  # total chlorine (ppm)
    'pH',  # pH (unitless)
    'TA',  # total alkilinity (ppm)
    'CA',  # calcium hardness (ppm)
    'pool_temp',  # temperature (*C)
    'air_temp',  # temperature (*C)
]

DIAGNOSTICS = [
    'CPU_TEMP',  # temperature (*C)
    'UP_TIME',  # in (s)
]

readings = {}
events = {}

context = {
    'last_compensation_temp': 20.0
}

settings = {
    # how often to take a reading; can be zero to pause readings (seconds)
    'read_frequency': 1,
    # send the compensation to the pH probe when the temperature changes
    # this much (degrees)
    'compensation_delta': 1.0,
}


def get_millis():
    '''Returns the current time, as an int, in millis'''
    return int(time.time() * 1000)


def as_millis(time_value):
    '''Converts python float time to millis'''
    return int(time_value * 1000)


def add_reading(reading):
    '''Add a new reading manually'''
    now = get_millis()
    for rt in READING_TYPES:
        if rt not in reading:
            reading[rt] = 'null'
    readings[now] = reading
    return now


def get_readings(after, before):
    '''Returns readings between after and before, inclusive.'''
    return {when: readings[when] for when in readings if when >= after and when <= before}


def delete_readings(after, before):
    '''Deletes readings between after and before, inclusive.'''
    for when in [when for when in readings if when >= after and when <= before]:
        del readings[when]


def get_events(after, before):
    '''Returns events between after and before, inclusive.'''
    return {when: events[when] for when in events if when >= after and when <= before}


def delete_event(after, before):
    '''Deletes events between after and before, inclusive.'''
    for when in [when for when in events if when >= after and when <= before]:
        del events[when]


def add_event(event):
    '''Add a new event'''
    now = get_millis()
    event[now] = event
    return now


def update_settings(new_settings):
    '''updates the current settings'''
    pass


def get_settings():
    '''returns the current settings'''
    return settings


def should_compensate(water_temp):
    '''Returns true if temperature compensation should be applied'''
    return abs(water_temp - context['last_compensation_temp']) > settings['compensation_delta']


def update_compensation_temp(water_temp):
    '''Sets the last known water compenstation temperature'''
    context['last_compenstation_temp'] = water_temp


def get_averages():
    '''Returns a recent, rolling average of data values'''
    return {}
