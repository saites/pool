'''
Handles communication with a database or memory cache
'''
import sqlite3
import time

CONN = sqlite3.connect('pool.db')
DB_VERSION = 1


def _construct_queries(name_types, table):
    '''Create and return the CREATE, INSERT, SELECT, and DELETE queries
    as well as a dictionary of names to columns'''
    definitions = ['{} {}'.format(name, typ) for name, typ in name_types]
    names = [name for name, _ in name_types]
    create = 'CREATE TABLE IF NOT EXISTS {} ({})'.format(
        table, ', '.join(definitions))
    insert = 'INSERT INTO {}({}) values({})'.format(
        table, ', '.join(names), ', '.join(['?'] * len(names)))
    delete = 'DELETE FROM {} WHERE ts >= ? AND ts <= ?'.format(
        table)
    ids = {n: i for i, n in enumerate(names)}
    return {'create': create, 'insert': insert, 'delete': delete, 'indexes': ids}


def select(table, columns='*', time_tuple=None):
    '''Performs a select against a particular table
    By default, selects all columns with no selection criteria.
    If provide, selects a subset of columns=['c1', 'c2'], etc.
    If provided, performs WHERE & ORDER BY on ts using (after, before) tuple.
    '''
    query = 'SELECT {} FROM {}'.format(', '.join(columns), table)
    if time_tuple is not None:
        query += ' WHERE ts >= ? AND ts <= ? ORDER BY ts'
        return CONN.execute(query, time_tuple)
    return CONN.execute(query)


EVENT_TYPES = [
    'ADD-CL',  # add chlorine (gals)
    'ADD-ACID',  # add acid (gals)
    'ADD-ALGAECIDE',  # add algaecide (liters)
    'SWIM',  # swim load (num people)
    'BACKWASH',  # backwash filter
    'CLEAN-FILTER',  # clean filter
    'WEATHER',  # what type of weather event
]

READINGS_COLS = [
    ('ts', 'INTEGER PRIMARY KEY'),  # reading timestamp (ms since epoch)
    ('fc', 'REAL'),  # free chlorine (ppm)
    ('tc', 'REAL'),  # total chlorine (ppm)
    ('ph', 'REAL'),  # pH (unitless)
    ('ta', 'INTEGER'),  # total alkilinity (ppm)
    ('ca', 'INTEGER'),  # calcium hardness (ppm)
    ('pool_temp', 'REAL'),  # temperature (*C)
    ('air_temp', 'REAL'),  # temperature (*C)
    ('cpu_temp', 'REAL'),  # temperature (*C)
    ('event', 'TEXT'),  # event that occurred at time of reading
    ('comment', 'TEXT'),  # event comments
]

SETTINGS_COLS = [
    ('id', 'INTEGER PRIMARY KEY'),
    ('name', 'TEXT'),
    ('value', 'TEXT'),
]
SETTINGS_TYPES = {
    # when the pi was turned on last (epoch)
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

TABLES = ['settings', 'readings']
TABLES_TO_COLS = {
    'settings': SETTINGS_COLS,
    'readings': READINGS_COLS,
}
QUERIES = {table_name: _construct_queries(TABLES_TO_COLS[table_name], table_name)
           for table_name in TABLES_TO_COLS}


def setup_database():
    '''Creates the initial database tables'''
    needs_settings = False
    try:
        dbv = int(CONN.execute(
            'SELECT * FROM settings WHERE what = database_version').fetchone())
        if dbv != DB_VERSION:
            raise Exception('DB needs schema migration')
    except sqlite3.DatabaseError:
        needs_settings = True

    for table_name in TABLES:
        CONN.execute(QUERIES[table_name]['create'])

    if needs_settings:
        for name in SETTINGS_TYPES:
            _, initial = SETTINGS_TYPES[name]
            CONN.execute('INSERT INTO settings(name, value) values(?, ?)',
                         (name, initial))
        CONN.commit()


setup_database()


def update_setting(key, value, delay_commit=False):
    '''updates the current settings'''
    # verify the key exists and the value is the right type while updating the internal settings
    _settings[key] = SETTINGS_TYPES[key][0](value)
    print(key, value)
    CONN.execute(
        'UPDATE settings SET value = ? WHERE name = ?', (key, value))
    if not delay_commit:
        CONN.commit()


_settings = {k: SETTINGS_TYPES[k][0](v)
             for _, k, v in CONN.execute('SELECT * FROM settings')}


def get_settings():
    '''returns all the current settings'''
    return _settings


def do_insert(table_name, values, with_ts=False):
    '''inserts the values into the named table'''
    if with_ts and 'ts' not in values:
        now = int(time.time() * 1000)
        values['ts'] = now
    else:
        now = values['ts']
    cols = TABLES_TO_COLS[table_name]
    to_insert = tuple(
        values[name] if name in values else None for name, _ in cols)
    CONN.execute(QUERIES[table_name]['insert'], to_insert)
    CONN.commit()
    return now


def do_get(table_name, after, before):
    '''returns the values from the table between the timestamps'''
    query = QUERIES[table_name]['select']
    return CONN.execute(query, (after, before)).fetchall()


def do_delete(table_name, after, before):
    '''delete values from the named table between the timestamps'''
    query = QUERIES[table_name]['delete']
    CONN.execute(query, (after, before))
    CONN.commit()


def add_reading(reading):
    '''Add a new reading manually'''
    return do_insert('readings', reading, True)


def get_readings(after, before):
    '''Returns readings between after and before, inclusive.'''
    return select('readings', time_tuple=(after, before)).fetchall()


def get_events(after, before):
    return select('readings', columns=['ts', 'event', 'column'], time_tuple=(after, before)).fetchall()


def delete_readings(after, before):
    '''Deletes readings between after and before, inclusive.'''
    do_delete('readings', after, before)


def update_settings(settings):
    '''update a group of settings as {key: value, key:value}'''
    try:
        for key, value in settings():
            update_setting(key, value)
        CONN.commit()
    except sqlite3.DatabaseError:
        CONN.rollback()


def should_compensate(water_temp):
    '''Returns true if temperature compensation should be applied'''
    return abs(water_temp - _settings['compensation_temp']) > _settings['compensation_delta']


def get_averages():
    '''Returns a recent, rolling average of data values'''
    return {}
