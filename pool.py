'''
Pool module for defining Flask routes to store and update info
'''

import functools
import time

from flask import Flask, request, jsonify, abort, render_template
import flask

import sensors
import dal
import schedule

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
schedule.set_reading_interval(dal.get_settings()['reading_interval'])
dal.update_setting('start_up_time', time.time())


def return_json(func):
    '''Decorator to return json from a function'''
    @functools.wraps(func)
    def inner(*a, **k):
        '''jsonify wrapper'''
        return jsonify(func(*a, **k))
    return inner


def extract_int(name, default=None):
    '''Extracts a float from the query parameters'''
    try:
        return int(request.args[name])
    except KeyError:
        return default
    except ValueError:
        abort(400, name + ' should be an int')


def extract_float(name, default=None):
    '''Extracts a float from the query parameters'''
    try:
        return float(request.args[name])
    except KeyError:
        return default
    except ValueError:
        abort(400, name + ' should be a float')


def extract_str(name, default=None):
    '''Extracts a string from the query parameters'''
    try:
        return request.args[name]
    except KeyError:
        return default


@app.route('/')
def get_index():
    '''Creates and returns the index page'''
    indexes = dal.QUERIES['readings']['indexes']

    to_return = [
        'fc', 'tc', 'ph', 'ta', 'ca'
    ]

    categories = []
    for name in to_return:
        display, units = dal.READING_INFO[name]
        value, when = dal.get_most_recent(name)
        print(value, when)
        categories.append(
            {
                'name': display,
                'value': str(value) if value is not None else '-',
                'unit': units,
                'when': when if when is not None else '-'
            }
        )
    return render_template('dashboard.html', categories=categories)


@app.route('/readings/csv')
def get_readings_csv():
    '''Returns requested readings as a csv'''
    after = extract_float('after', 0)
    before = extract_float('before', int(1000 * time.time()))
    readings = dal.get_readings(after, before)

    indexes = dal.QUERIES['readings']['indexes']

    def generate():
        yield ','.join(indexes) + '\n'
        for r in readings:
            yield ','.join([str(_) for _ in r]) + '\n'
    return flask.Response(generate(), mimetype='text/csv')


@app.route('/readings/datatable')
@return_json
def get_readings_datatable():
    '''Returns a Google Visualization DataTable format
    for the requested data'''
    after = extract_float('after', 0)
    before = extract_float('before', int(1000 * time.time()))
    readings = dal.get_readings(after, before)

    indexes = dal.QUERIES['readings']['indexes']
    when_idx = indexes['ts']
    pH_idx = indexes['ph']
    pool_temp_idx = indexes['pool_temp']
    event_idx = indexes['event']

    chart_data = {
        'cols': [
            {'id': 'when', 'label': 'Time', 'type': 'datetime'},
            {'id': 'event', 'type': 'string', 'role': 'annotation'},
            {'id': 'pH', 'label': 'pH', 'type': 'number'},
            {'id': 'pool_temp', 'label': 'Pool Temperature', 'type': 'number'}
        ],
        'rows': [
            {'c': [
                {'v': 'Date({})'.format(r[when_idx])},
                {'v': r[event_idx]},
                {'v': r[pH_idx]},
                {'v': r[pool_temp_idx]}
            ]} for r in readings
        ]
    }
    return chart_data


@app.route('/readings', methods=['GET', 'POST', 'DELETE'])
@return_json
def handle_reading():
    '''Get or record a reading'''
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
    '''Takes a reading immediately and returns its value'''
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

    if 'store' in request.args and str_to_bool(request.args['store']):
        dal.add_reading(reading)

    return reading


def str_to_bool(string):
    return string.lower() in ['t', 'true', '1', 'y']


@app.route('/events')
@return_json
def handle_event():
    '''Get events'''
    after = extract_float('after', 0)
    before = extract_float('before', int(1000 * time.time()))
    return dal.get_events(after, before)


@app.route('/settings', methods=['GET', 'PUT'])
@return_json
def handle_settings():
    '''Get or update settings'''
    # should be {setting: value}
    if request.method == 'PUT':
        new_settings = request.get_json()
        dal.update_settings(new_settings)
        updated_settings = dal.get_settings()
        if 'reading_interval' in updated_settings:
            schedule.set_reading_interval(updated_settings['reading_interval'])
        return updated_settings
    else:
        return dal.get_settings()
