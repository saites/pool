'''
Pool module for defining Flask routes to store and update info
'''

import functools
import time

from flask import Flask, request, jsonify, abort, render_template, flash
from sqlalchemy.exc import IntegrityError
import flask

from forms import ManualReadingForm
import sensors
import dal
import schedule
import secret_key

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
secret_key.set_secret_key(app)

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
    to_return = [
        'fc', 'tc', 'ph', 'ta', 'ca', 'cya'
    ]

    categories = []
    for name in to_return:
        display, units = dal.Reading.info[name]
        r = dal.get_most_recent(name)
        categories.append(
            {
                'name': display,
                'value': str(getattr(r, name)) if r is not None else '-',
                'unit': units,
                'when': r.ts if r is not None else '-'
            }
        )
    return render_template('dashboard.html', categories=categories)


@app.route('/readings/manual', methods=['GET', 'POST'])
def get_manual_reading_page():
    '''Creates and returns the manual readings form'''
    form = ManualReadingForm(request.form)
    if request.method == 'POST' and form.validate():
        reading = {
            'fc': form.fc.data,
            'tc': form.tc.data,
            'ph': form.ph.data,
            'ta': form.ta.data,
            'ca': form.ca.data,
            'cya': form.cya.data,
            'ts': int(time.mktime(form.when.data.timetuple()) * 1000)
        }
        try:
            r = dal.add_reading(reading)
        except IntegrityError as e:
            flash('A reading for that time already exists')
            return flask.redirect('/readings/manual')

        if form.event.data != '':
            print(form.event.data)
            event = {
                'event_type': form.event.data,
                'comment': form.comment.data if form.comment.data != '' else None
            }
            dal.add_event(r, event)
        flash('Reading added')
        return flask.redirect('/readings/manual')
    return render_template('add_reading.html', form=form)


@app.route('/readings/list', methods=['GET', 'POST'])
def get_readings_list():
    after = extract_float('after', 0)
    before = extract_float('before', int(1000 * time.time()))
    readings = dal.get_readings(after, before)

    to_return = [
        'fc', 'tc', 'ph', 'ta', 'ca', 'cya'
    ]

    categories = []
    r = readings[0]
    for name in to_return:
        display, units = dal.Reading.info[name]
        categories.append(
            {
                'name': display,
                'value': getattr(r, name),
                'unit': units,
                'when': r.ts
            }
        )
        print(str(getattr(r, name)))

    return render_template('display_readings.html', readings=readings,
                           categories=categories)


@app.route('/readings/csv')
def get_readings_csv():
    '''Returns requested readings as a csv'''
    after = extract_float('after', 0)
    before = extract_float('before', int(1000 * time.time()))
    readings = dal.get_readings(after, before)

    indexes = [d[0] for d in dal.Reading.definitions]

    def generate():
        yield ','.join(indexes) + '\n'
        for r in readings:
            yield str(r) + '\n'
    return flask.Response(generate(), mimetype='text/csv')


@app.route('/readings/datatable')
@return_json
def get_readings_datatable():
    '''Returns a Google Visualization DataTable format
    for the requested data'''
    after = extract_float('after', 0)
    before = extract_float('before', int(1000 * time.time()))
    readings = dal.get_readings(after, before)

    chart_data = {
        'cols': [
            {'id': 'when', 'label': 'Time', 'type': 'datetime'},
            {'id': 'event', 'type': 'string', 'role': 'annotation'},
            {'id': 'pH', 'label': 'pH', 'type': 'number'},
            {'id': 'pool_temp', 'label': 'Pool Temperature', 'type': 'number'}
        ],
        'rows': [
            {'c': [
                {'v': 'Date({})'.format(r.ts)},
                {'v': r.get_events_str()},
                {'v': r.ph},
                {'v': r.pool_temp}
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
        return dal.add_reading(request.get_json())
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
