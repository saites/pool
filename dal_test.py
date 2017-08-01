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


print(dal.get_reading_at(1).events.all())
'''
print(dal.get_events(1, 3))
print(dal.get_event_at(1))
print(dal.get_event_at(1).reading)
'''
