'''
Defines the backend events APIs 
'''
from flask import Blueprint, abort
from pool.utils.flask_utils import *
from pool.backend import dal

events = Blueprint('events', __name__)


@events.route('/', methods=['GET', 'DELETE'])
@return_json
def handle_event():
    '''Get or delete events'''
    if request.method == 'DELETE':
        data = request.get_json()
        try:
            event_id = int(data['event_id'])
        except KeyError:
            abort(400, 'missing event_id')
        dal.delete_event_by_id(event_id)
    else:
        after = extract_float('after', 0)
        before = extract_float('before', int(1000 * time.time()))
        return dal.get_events(after, before)
