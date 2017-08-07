from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc, event
from sqlalchemy.engine import Engine
import time

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pool.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

DATABASE_VERSION = 1


@event.listens_for(Engine, "connect")
def set_sqlite_pragmas(dbapi_connection, connection_record):
    '''defines pragmas for use with the database connection'''
    cursor = dbapi_connection.cursor()
    cursor.execute('PRAGMA foreign_keys=ON')
    cursor.close()


def as_dict(db_model):
    '''Returns a db model object as a dict'''
    return {c.name: getattr(db_model, c.name) for c in db_model.__table__.columns}


def get_or_default(dict, key, default=None):
    '''Extracts a key from a dict, or returns a default value'''
    try:
        return dict[key]
    except KeyError:
        return default


class Reading(db.Model):
    '''Represents a pool reading.
    ts is when the reading was taken, and is always defined.
        If ts isn't defined at creation, it is automatically
        set to the system's current time (in ms since epcoh).
    All other values are optional, and can be specified as
        **kwarsg.
    '''
    __tablename__ = 'reading'
    ts = db.Column(db.Integer, primary_key=True)
    fc = db.Column(db.Float)
    tc = db.Column(db.Float)
    ph = db.Column(db.Float)
    ta = db.Column(db.Integer)
    ca = db.Column(db.Integer)
    cya = db.Column(db.Integer)
    pool_temp = db.Column(db.Float)
    air_temp = db.Column(db.Float)
    cpu_temp = db.Column(db.Float)
    events = db.relationship('Event',
                             backref='reading',
                             cascade='all, delete-orphan',
                             passive_deletes=True)

    definitions = [
        ('ts', 'timestamp', 'ms since epoch'),
        ('fc', 'Free Cl', 'ppm'),
        ('tc', 'Total Cl', 'ppm'),
        ('ph', 'pH', ''),
        ('ta', 'Total Alkilinity', 'ppm'),
        ('ca', 'Calcium Hardness', 'ppm'),
        ('cya', 'CYA', 'ppm'),
        ('pool_temp', 'Pool Temperature', '*C'),
        ('cpu_temp', 'CPU Temperature', '*C'),
        ('air_temp', 'Air Temperature', '*C'),
    ]
    info = {d[0]: (d[1], d[2]) for d in definitions}

    def __init__(self, **kwargs):
        bad_args = [arg for arg in kwargs if arg not in self.info]
        if any(bad_args):
            raise Exception('kwargs includes unknown arguments: ' +
                            ', '.join(bad_args))
        self.ts = get_or_default(kwargs, 'ts', int(time.time() * 1000))
        self.fc = get_or_default(kwargs, 'fc')
        self.tc = get_or_default(kwargs, 'tc')
        self.ph = get_or_default(kwargs, 'ph')
        self.ta = get_or_default(kwargs, 'ta')
        self.ca = get_or_default(kwargs, 'ca')
        self.cya = get_or_default(kwargs, 'cya')
        self.pool_temp = get_or_default(kwargs, 'pool_temp')
        self.air_temp = get_or_default(kwargs, 'air_temp')
        self.cpu_temp = get_or_default(kwargs, 'cpu_temp')

    def __repr__(self):
        return ','.join([str(getattr(self, d[0])) for d in Reading.definitions])

    def get_events_str(self):
        if len(self.events) == 0:
            return None
        return '\n'.join([str(e) for e in self.events])


EVENT_TYPES = {
    'ADD-CL': ('Add chlorine', 'gal'),
    'ADD-ACID': ('Add acid', 'gal'),
    'ADD-ALGAECIDE': ('Add algaecide', 'liter'),
    'SWIM': ('Swim load', 'num people'),
    'BACKWASH': ('Backwash filter', ''),
    'CLEAN-FILTER': ('Clean filter', ''),
    'WEATHER': ('Weather event', ''),
}


class DalException(Exception):
    pass


class Event(db.Model):
    '''
    Events represent one of a set of things that could have
        been done to the pool. They are always attached to a
        particular reading, which defines their timestamp.
        A Reading can have zero or more Events.
    The meaning of the event quantity is dependent on
        the event type.
    You can also define a comment about that particular event.
    '''
    __tablename__ = 'event'
    event_id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(80))
    quantity = db.Column(db.Float)
    comment = db.Column(db.Text)

    reading_ts = db.Column(db.Integer,
                           db.ForeignKey('reading.ts', ondelete='CASCADE'))

    definitions = [
        ('event_type', 'Event Type', ''),
        ('quantity', 'Event Quantity', ''),
        ('comment', 'Event Comment', ''),
    ]
    info = {d[0]: (d[1], d[2]) for d in definitions}

    def __init__(self, reading, **kwargs):
        if reading == None:
            raise DalException('reading must be supplied')
        if 'event_type' not in kwargs:
            raise DalException('event_type must be supplied')
        if kwargs['event_type'] not in EVENT_TYPES:
            raise DalException('Unknown event type')

        self.reading = reading
        self.event_type = kwargs['event_type']
        self.quantity = get_or_default(kwargs, 'quantity')
        self.comment = get_or_default(kwargs, 'comment')

    def __repr__(self):
        desc, unit = EVENT_TYPES[self.event_type]
        parts = [desc]
        if self.quantity:
            parts += [' (', str(self.quantity)]
            if unit:
                parts += [' ', unit]
            parts += [')']
        if self.comment:
            parts += [': ', self.comment]
        return ''.join(parts)


SETTINGS_TYPES = {
    # when the pi was turned on last (s since epoch)
    'start_up_time': (int, 0),
    # how often to take a new reading (s)
    'reading_interval': (int, 60),
    # last temperature used for pH comp (*C)
    'compensation_temp': (int, 25),
    # how for the temp should drift before update
    'compensation_delta': (int, 1),
    # current db version
    'database_version': (int, 1),
}


class Setting(db.Model):
    '''
    Settings are key,value pairs which define properties
        of the system.
    A setting's key must be one of the predefined
        SETTINGS_TYPES.
    The value's context is dependent on its type, and a
        converted value can be secured by calling get_value().
        The class will convert it according to its setting type.
    '''
    name = db.Column(db.String(80), primary_key=True)
    value = db.Column(db.String(80))

    definitions = [
        ('name', 'Setting Name', ''),
        ('value', 'Setting Value', ''),
    ]
    info = {d[0]: (d[1], d[2]) for d in definitions}

    def __init__(self, name, value):
        if name not in SETTINGS_TYPES:
            raise ValueError('Unknown setting {}'.format(name))
        self.name = name
        self.value = value

    def __repr__(self):
        converted = SETTINGS_TYPES[self.name][0](self.value)
        return '{}: {}'.format(self.name, converted)

    def get_value(self):
        try:
            converter = SETTINGS_TYPES[self.name][0]
        except KeyError:
            raise Exception('No setting known for {}'.format(self.name))
        return converter(self.value)


def _setup_database():
    '''
    Performs initial database setup. It is safe to call
    this method even after the database has been set up.
    If the database version has changed from the value
    stored in the database, then this method throws; in
    that case, a migration procedure should be developed. 
    This is automatically called upon import.
    '''
    db.create_all()

    # check database version
    cur_version = Setting.query.get('database_version')
    if cur_version != None:
        if cur_version.get_value() == DATABASE_VERSION:
            return
        raise Exception('DB needs schema migration from {} to {}'
                        .format(cur_version.get_version(), DATABASE_VERSION))

    # initilize settings
    for name in SETTINGS_TYPES:
        _, initial = SETTINGS_TYPES[name]
        s = Setting(name, str(initial))
        db.session.add(s)
    db.session.commit()


_setup_database()
_settings = {s.name: s.get_value() for s in Setting.query.filter().all()}


def add_reading(json_reading):
    '''Convert JSON into a reading object'''
    r = Reading(**json_reading)
    db.session.add(r)
    db.session.commit()
    return r


def _get_readings_query(after, before):
    return Reading.query.filter(Reading.ts >= after, Reading.ts <= before)


def get_readings(after, before):
    return _get_readings_query(after, before)\
        .order_by(desc(Reading.ts))\
        .all()


def get_reading_at(reading_ms):
    return Reading.query.filter(Reading.ts == reading_ms).first()


def get_most_recent(reading_type):
    col = getattr(Reading, reading_type)
    return Reading.query\
        .order_by(desc(Reading.ts))\
        .filter(col != None)\
        .first()


def add_event(reading, json_event):
    e = Event(reading, **json_event)
    db.session.add(e)
    db.session.commit()
    return e


def add_event_by_time(reading_time, json_event):
    r = get_reading_at(reading_time)
    if r is None:
        raise DalException('No reading at {}'.format(reading_time))
    add_event(r, json_event)


def get_events(after, before):
    return Event.query.filter(Event.reading_ts >= after, Event.reading_ts <= before).all()


def get_events_at(reading_ms):
    return Event.query.filter(Event.reading_ts == reading_ms).all()


def get_events_by_kind(after, before, kind):
    return Event.query.filter(Event.reading_ts >= after,
                              Event.reading_ts <= before,
                              Event.event_type == kind).all()


def delete_readings(after, before):
    deleted = _get_readings.query(after, before).delete()
    db.session.commit()
    return deleted


def delete_event_by_id(event_id):
    deleted = Event.query.filter(Event.event_id == event_id).delete()
    db.session.commit()
    return deleted >= 1


def delete_reading_at(reading_ts):
    deleted = Reading.query.filter(Reading.ts == reading_ts).delete()
    db.session.commit()
    return deleted >= 1


def get_settings():
    return _settings


def get_setting_value(key):
    return Setting.query.filter_by(name=key).first().get_value()


def update_setting(key, value, delay_commit=False):
    if key == 'database_version':
        raise Exception(
            'Database version should not be changed programmatically')
    converted = SETTINGS_TYPES[key][0](value)
    _settings[key] = converted
    Setting.query.filter_by(name=key).update({Setting.value: str(converted)})
    if not delay_commit:
        db.session.commit()


def update_settings(setting_map):
    print(setting_map)
    try:
        for key in setting_map:
            value = setting_map[key]
            if value == '' or value == None:
                continue
            update_setting(key, value)
    except Exception as e:
        db.session.rollback()
        raise e
    db.session.commit()


def should_compensate(water_temp):
    '''Returns true if temperature compensation should be applied'''
    return abs(water_temp - _settings['compensation_temp']) > _settings['compensation_delta']
