'''
Pool module to configure the Flask application object 
'''
import time
import os
import flask
import flask_sijax

# setup Flask; since @app decorators rely on this module, this must
# happen before importing pool submodules
app = flask.Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
import pool.secret_key
import pool.html_routes
import pool.error_handlers

# configure Sijax
sijax_path = os.path.join('.', os.path.dirname(__file__), 'static/js/sijax/')
app.config['SIJAX_STATIC_PATH'] = sijax_path
app.config['SIJAX_JSON_URI'] = '/static/js/sijax/json2.js'
flask_sijax.Sijax(app)

# start the reading job and update the start up time
from pool.backend import dal
import pool.schedule as schedule
schedule.set_reading_interval(dal.get_settings()['reading_interval'])
dal.update_setting('start_up_time', time.time())
