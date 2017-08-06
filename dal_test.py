import dal
import time

dal.Reading.query.filter().delete()
dal.Event.query.filter().delete()

elems = [
    {
        'ts': 1,
        'tc': 0,
        'fc': 7.5,
        'ph': 7.4,
    },
    {
        'ts': 2,
        'fc': 10.0,
        'ph': 7.5
    },
    {
        'ts': 3,
        'ta': 150
    },
]

for e in elems:
    dal.add_reading(e)

assert len(dal.get_readings(1, 3)) == 3
assert dal.get_most_recent('fc').fc == 10.0

dal.add_event_by_time(1, {
    'event_type': 'ADD-CL',
    'comment': 'added it quickly',
    'quantity': 1.0,
})
dal.add_event_by_time(1, {
    'event_type': 'ADD-ACID',
    'comment': 'just for fun',
    'quantity': 2.0,
})

assert len(dal.get_events(1, 3)) == 2
assert len(dal.get_events_at(1)) == 2
assert len(dal.get_events_by_kind(1, 3, 'ADD-CL')) == 1

event_id = dal.get_events_at(1)[0].event_id
assert dal.delete_event_by_id(event_id) == True
assert dal.delete_event_by_id(event_id) == False
assert len(dal.get_events_at(1)) == 1
assert dal.delete_reading_at(1) == True
assert len(dal.get_events_at(1)) == 0
assert len(dal.get_readings(1, 3)) == 2


dal.update_setting('reading_interval', 30)
assert dal.get_setting_value('reading_interval') == 30
dal.update_setting('reading_interval', 60)
assert dal.get_setting_value('reading_interval') == 60


dal.update_setting('compensation_temp', 25)
dal.update_setting('compensation_delta', 1)
assert dal.should_compensate(25) == False
assert dal.should_compensate(26) == False
assert dal.should_compensate(27) == True
dal.update_setting('compensation_temp', 27)
assert dal.should_compensate(27) == False
dal.update_setting('compensation_delta', 5)
assert dal.should_compensate(22) == False
dal.update_setting('compensation_temp', 25)
dal.update_setting('compensation_delta', 1)
