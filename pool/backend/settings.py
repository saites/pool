'''
Defines the backend settings APIs 
'''
from flask import Blueprint, abort
from pool.utils.flask_utils import *

settings = Blueprint('settings', __name__)


@settings.route('/', methods=['GET', 'PUT'])
@return_json
def handle_settings():
    '''Get or update settings as json, as {setting: value}'''
    if request.method == 'PUT':
        new_settings = request.get_json()
        dal.update_settings(new_settings)
        updated_settings = dal.get_settings()
        if 'reading_interval' in updated_settings:
            schedule.set_reading_interval(updated_settings['reading_interval'])
        return updated_settings
    else:
        return dal.get_settings()
