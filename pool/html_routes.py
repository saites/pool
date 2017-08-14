from pool import app

import datetime
from flask import request, render_template, flash, redirect
from sqlalchemy.exc import IntegrityError

from pool.utils.flask_utils import *
from pool.backend import dal
from pool.utils.calcs import saturation_index
from pool.forms import ManualReadingForm, SettingsForm
import pool.schedule

# configure sub-routes
import pool.backend.readings
import pool.backend.events
import pool.backend.settings
app.register_blueprint(pool.backend.readings.readings,
                       url_prefix='/backend/readings')
app.register_blueprint(pool.backend.events.events,
                       url_prefix='/backend/events')
app.register_blueprint(pool.backend.settings.settings,
                       url_prefix='/backend/settings')


@app.route('/')
def get_index():
    '''Dashboard page'''
    to_return = [
        'fc', 'tc', 'ph', 'ta', 'ca', 'cya', 'pool_temp'
    ]
    readings = {n: dal.get_most_recent(n) for n in to_return}
    values = {n: getattr(readings[n], n) if readings[n] is not None else None
              for n in to_return}

    categories = []
    for name in to_return:
        display, units = dal.Reading.info[name]
        r = readings[name]
        v = values[name]
        categories.append(
            {
                'name': display,
                'value': str(v) if r is not None else '-',
                'unit': units,
                'when': r.ts if r is not None else '-'
            }
        )

    SI = saturation_index(
        values['ph'], values['pool_temp'], values['ca'], values['ta'])
    categories.append({
        'name': 'Sat. Index',
        'value': '{:.3}'.format(SI) if SI is not None else '-',
        'units': '',
        'when': 'Calculated'
    })
    return render_template('dashboard.html', categories=categories)


@app.route('/readings')
def get_readings():
    '''Page to display readings'''
    return render_template('display_readings.html')


@app.route('/readings/list')
def get_readings_list():
    after = extract_int('after', 0)
    before = extract_int('before', int(1000 * time.time()))
    readings = dal.get_readings(after, before)
    return render_template('reading_list.html', readings=readings)


def _handle_individual_reading(edit_mode=False, ts=None):
    '''Page to creates new readings'''
    form = ManualReadingForm(request.form)
    if request.method == 'POST' and form.validate():
        reading = {
            'fc': form.fc.data,
            'tc': form.tc.data,
            'ph': form.ph.data,
            'ta': form.ta.data,
            'ca': form.ca.data,
            'cya': form.cya.data,
            'pool_temp': form.pool_temp.data,
            'ts': int(time.mktime(form.when.data.timetuple()) * 1000)
        }
        try:
            r = dal.add_reading(reading)
        except IntegrityError as e:
            flash('A reading for that time already exists')
            return redirect('/readings/add')

        if form.event_type.data != '':
            print(form.event_type.data)
            event = {
                'event_type': form.event_type.data,
                'quantity': form.event_quantity.data if form.event_quantity.data != '' else None,
                'comment': form.event_comment.data if form.event_comment.data != '' else None
            }
            dal.add_event(r, event)
        flash('Reading added')
        return redirect('/readings') if edit_mode else redirect('/readings/add')
    else:
        if edit_mode:
            try:
                ts_int = int(ts)
            except ValueError:
                flash("Didn't understand that timestamp")
                return redirect('/readings')

            reading = dal.get_reading_at(ts_int)
            if reading == None:
                flash("Couldn't find a reading at {}".format(ts_int))
                return redirect('/readings')

            form.when.data = datetime.datetime.fromtimestamp(ts_int / 1000)
            form.fc.data = reading.fc
            form.tc.data = reading.tc
            form.ph.data = reading.ph
            form.ta.data = reading.ta
            form.ca.data = reading.ca
            form.cya.data = reading.cya
            form.pool_temp.data = reading.pool_temp
            if any(reading.events):
                e = reading.events[0]
                form.event_type.data = e.event_type
                form.event_quantity.data = e.event_quantity
                form.event_comment.data = e.event_comment

        return render_template('add_reading.html', form=form, edit_mode=edit_mode)


@app.route('/readings/add', methods=['GET', 'POST'])
def get_manual_reading_page():
    '''Page to add readings'''
    return _handle_individual_reading()


@app.route('/readings/edit/<ts>', methods=['GET', 'POST'])
def edit_reading(ts):
    '''Page to edit readings'''
    return _handle_individual_reading(edit_mode=True, ts=ts)


@app.route('/settings', methods=['GET', 'POST'])
def display_settings():
    '''Page to view and modify settings'''
    form = SettingsForm(request.form)
    if request.method == 'POST' and form.validate:
        new_settings = {
            'compensation_delta': form.comp_delta.data,
            'reading_interval': form.reading_interval.data
        }
        dal.update_settings(new_settings)
        updated_settings = dal.get_settings()
        pool.schedule.set_reading_interval(
            updated_settings['reading_interval'])
        return redirect('/settings')
    else:
        settings = dal.get_settings()
        return render_template('settings.html', form=form, settings=settings)
