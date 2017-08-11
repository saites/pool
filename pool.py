'''
Pool module for defining Flask routes to store and update info
'''

import functools
import time
import os

from flask import Flask, request, jsonify, abort, render_template, flash
from sqlalchemy.exc import IntegrityError
import flask
import flask_sijax

from forms import ManualReadingForm, SettingsForm
import sensors
import dal
import schedule
import secret_key

path = os.path.join('.', os.path.dirname(__file__), 'static/js/sijax/')

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SIJAX_STATIC_PATH'] = path
app.config['SIJAX_JSON_URI'] = '/static/js/sijax/json2.js'
flask_sijax.Sijax(app)
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
    '''Extracts an int from the query parameters'''
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


@app.template_filter('ms_to_str')
def ms_to_str(ms):
    '''Provides a common formatter for ms to strings'''
    return time.strftime('%a, %d %b %Y at %H:%M:%S', time.localtime(ms / 1000))


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
    '''Creates and handle the manual readings form'''
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

        if form.event_type.data != '':
            print(form.event_type.data)
            event = {
                'event_type': form.event_type.data,
                'quantity': form.event_quantity.data if form.event_quantity.data != '' else None,
                'comment': form.event_comment.data if form.event_comment.data != '' else None
            }
            dal.add_event(r, event)
        flash('Reading added')
        return flask.redirect('/readings/manual')
    return render_template('add_reading.html', form=form)


@app.route('/readings/list', methods=['GET', 'POST'])
def get_readings_list():
    def remove_reading(obj_response, ts):
        dal.delete_reading_at(int(ts))

    if flask.g.sijax.is_sijax_request:
        flask.g.sijax.register_callback('remove_reading', remove_reading)
        return flask.g.sijax.process_request()

    return render_template('display_readings.html')


@app.route('/readings/csv', methods=['GET'])
def get_readings_csv():
    '''Returns requested readings as a csv'''
    after = extract_int('after', 0)
    before = extract_int('before', int(1000 * time.time()))
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
    after = extract_int('after', 0)
    before = extract_int('before', int(1000 * time.time()))
    readings = dal.get_readings(after, before)

    chart_data = {
        'cols': [
            {'id': 'when', 'label': 'Time', 'type': 'datetime'},
            {'id': 'event', 'type': 'string', 'role': 'annotation'},
            {'id': 'pH', 'label': 'pH', 'type': 'number'},
            {'id': 'fc', 'label': 'Free Chlorine', 'type': 'number'},
            {'id': 'tc', 'label': 'Total Chlorine', 'type': 'number'},
            {'id': 'pool_temp', 'label': 'Pool Temperature', 'type': 'number'}
        ],
        'rows': [
            {'c': [
                {'v': 'Date({})'.format(r.ts)},
                {'v': None},  # r.get_events_str()},
                {'v': r.ph},
                {'v': r.fc},
                {'v': r.tc},
                {'v': r.pool_temp}
            ]} for r in readings
        ]
    }
    return chart_data


@app.route('/readings', methods=['GET', 'POST', 'DELETE'])
def handle_reading():
    '''Get or record a reading'''
    if request.method == 'DELETE':
        data = request.get_json()
        try:
            ts = int(data['ts'])
        except KeyError:
            abort(400, '')
        dal.delete_reading_at(ts)
        return jsonify({"response": "OK"})
    if request.method == 'POST':
        return jsonify(dal.add_reading(request.get_json()))
    else:
        after = extract_int('after', 0)
        before = extract_int('before', int(1000 * time.time()))
        readings = dal.get_readings(after, before)
        return render_template('reading_list.html', readings=readings)


@app.route('/readings/raw', methods=['GET'])
@return_json
def handle_raw_readings():
    after = extract_int('after', 0)
    before = extract_int('before', int(1000 * time.time()))
    return [dal.as_dict(r) for r in dal.get_readings(after, before)]


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


@app.route('/settings', methods=['GET', 'POST'])
def handle_settings():
    '''Get or update settings'''
    # should be {setting: value}

    form = SettingsForm(request.form)

    if request.method == 'PUT':
        new_settings = request.get_json()
        dal.update_settings(new_settings)
        updated_settings = dal.get_settings()
        if 'reading_interval' in updated_settings:
            schedule.set_reading_interval(updated_settings['reading_interval'])
        return updated_settings
    if request.method == 'POST' and form.validate:
        new_settings = {
            'compensation_delta': form.comp_delta.data,
            'reading_interval': form.reading_interval.data
        }
        dal.update_settings(new_settings)
        updated_settings = dal.get_settings()
        schedule.set_reading_interval(updated_settings['reading_interval'])
        return flask.redirect('/settings')
    else:
        settings = dal.get_settings()
        return render_template('settings.html', form=form, settings=settings)
