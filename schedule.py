'''
Handles scheduled jobs for the pool software.
'''
import atexit
import requests

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import apscheduler

READING_JOB_ID = 'reading_job'
SCHEDULER = BackgroundScheduler()
SCHEDULER.start()
PORT = 5000
atexit.register(lambda: SCHEDULER.shutdown())


def _record_reading():
    '''Sends a request to record a reading.
    This operates over HTTP so that db interactions
    happen on the same thread.
    '''
    reading = requests.get(
        'http://localhost:{}/readings/current?store=true'.format(PORT))


def set_reading_interval(seconds):
    '''Sets up a job to regularly take readings. 
    If the interval is <= 0, no readings are taken. 
    '''
    if SCHEDULER.get_job(READING_JOB_ID) is None:
        if seconds <= 0:
            return
        SCHEDULER.add_job(
            func=_record_reading,
            trigger=IntervalTrigger(seconds=seconds),
            id=READING_JOB_ID
        )
    elif seconds > 0:
        SCHEDULER.reschedule_job(READING_JOB_ID,
                                 trigger=IntervalTrigger(seconds=seconds))
    else:
        SCHEDULER.pause_job(READING_JOB_ID)
