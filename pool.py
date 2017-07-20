'''
Pool module for defining Flask routes to store and update info
'''

import functools
import time
from flask import Flask, request, jsonify, abort, render_template
import flask

import sensors
import dal

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True


def return_json(func):
    '''Decorator to return json from a function'''
    @functools.wraps(func)
    def inner(*a, **k):
        '''jsonify wrapper'''
        return jsonify(func(*a, **k))
    return inner


def extract_float(name, default_val):
    '''Extracts a float from the query parameters'''
    try:
        return float(request.args[name])
    except KeyError:
        return default_val
    except ValueError:
        abort(400, name + ' should be a float')


@app.route('/')
def get_index():
    '''Creates and returns the index page'''
    print('   loading index')
    '''
    last_week = datetime.datetime.today() - datetime.timedelta(days=7)
    flask.g.readings = dal.get_readings(
        dal.as_millis(last_week.timestamp()), dal.get_millis())
    '''
    return render_template('dashboard.html')


@app.route('/readings/datatable')
@return_json
def get_readings_datatable():
    '''Returns a Google Visualization DataTable format
    for the requested data'''
    after = extract_float('after', 0)
    before = extract_float('before', int(1000 * time.time()))
    readings = dal.get_readings(after, before)
    indexes = dal.QUERIES['readings']['indexes']
    print(indexes)
    when_idx = indexes['ts']
    pH_idx = indexes['ph']
    pool_temp_idx = indexes['pool_temp']
    return {
        'cols': [
            {'id': 'when', 'label': 'Time', 'type': 'datetime'},
            {'id': 'pH', 'label': 'pH', 'type': 'number'},
            {'id': 'pool_temp', 'label': 'Pool Temperature', 'type': 'number'}
        ],
        'rows': [
            {'c': [
                {'v': millis_to_date(r[when_idx])},
                {'v': r[pH_idx]},
                {'v': r[pool_temp_idx]},
            ]} for r in readings
        ]
    }


def millis_to_date(millis):
    '''Returns a Google Visualization compatible
    string for a given millisecond representation'''
    return 'Date({})'.format(millis)


@app.route('/readings', methods=['GET', 'POST', 'DELETE'])
@return_json
def handle_reading():
    '''Get or create a reading'''
    if request.method == 'DELETE':
        after = extract_float('after', None)
        before = extract_float('before', None)
        if after is None or before is None:
            abort(400, 'after and before must both be specified')
        dal.delete_readings(after, before)
        return {"response": "OK"}
    if request.method == 'POST':
        now = dal.add_reading(request.get_json())
        return {'ts': now}
    else:
        after = extract_float('after', 0)
        before = extract_float('before', int(1000 * time.time()))
        return dal.get_readings(after, before)


@app.route('/readings/current')
@return_json
def take_reading():
    '''Takes a reading immediately, stores it, and returns its value'''
    water_temp = sensors.get_water_temperature()
    if dal.should_compensate(water_temp):
        dal.update_setting('compensation_delta', water_temp)
        sensors.set_pH_temp_compensation(water_temp)

    reading = {
        'pool_temp': water_temp,
        'ph': sensors.get_pH(),
        'air_temp': sensors.get_air_temperature(),
        'cpu_temp': sensors.get_internal_temperature()
    }

    reading['ts'] = dal.add_reading(reading)
    return reading


@app.route('/events', methods=['GET', 'POST'])
@return_json
def handle_event():
    '''Get or create events'''
    if request.method == 'POST':
        now = dal.add_event(request.get_json())
        return {'ts': now}
    else:
        after = extract_float('after', 0)
        before = extract_float('before', int(1000 * time.time()))
        return dal.get_events(after, before)


@app.route('/settings', methods=['GET', 'PUT'])
@return_json
def handle_settings():
    '''Get or update settings'''
    # should be {setting: value}
    if request.method == 'PUT':
        dal.update_settings(request.get_json)
    return dal.get_settings()
