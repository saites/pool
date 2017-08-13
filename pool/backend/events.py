'''
Defines the backend events APIs 
'''
from flask import Blueprint, abort
from pool.utils.flask_utils import *

events = Blueprint('events', __name__)


@events.route('/')
@return_json
def handle_event():
    '''Get events'''
    after = extract_float('after', 0)
    before = extract_float('before', int(1000 * time.time()))
    return dal.get_events(after, before)
