'''
Defines the backend readings APIs 
'''
from flask import Blueprint, abort
from pool.utils.flask_utils import *
from pool.backend import dal

readings = Blueprint('readings', __name__)


@readings.route('/', methods=['GET', 'POST', 'DELETE'])
@return_json
def handle_reading():
    '''Get or record a reading'''
    if request.method == 'DELETE':
        data = request.get_json()
        try:
            ts = int(data['ts'])
        except KeyError:
            abort(400, 'missing ts')
        dal.delete_reading_at(ts)
        return {"response": "OK"}
    if request.method == 'POST':
        return dal.add_reading(request.get_json())
    else:
        after = extract_int('after', 0)
        before = extract_int('before', int(1000 * time.time()))
        return [dal.as_dict(r) for r in dal.get_readings(after, before)]


@readings.route('/datatable')
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


@readings.route('/csv', methods=['GET'])
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


@readings.route('/current')
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
