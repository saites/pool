import functools
import time
from flask import jsonify, abort, request
from pool import app


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


def str_to_bool(string):
    return string.lower() in ['t', 'true', '1', 'y']


@app.template_filter('ms_to_str')
def ms_to_str(ms):
    '''Provides a common formatter for ms to strings'''
    try:
        return time.strftime('%a, %d %b %Y at %H:%M:%S', time.localtime(ms / 1000))
    except:
        return ms


class SelectOption():
    def __init__(self, value, display):
        self.value = value
        self.display = display
