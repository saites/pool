from wtforms import Form, DateTimeField, SelectField,\
    TextAreaField, StringField, IntegerField, FloatField

from wtforms.validators import Optional, DataRequired, NumberRange
from dal import EVENT_TYPES

event_d = {'': ''}
for formal, info in EVENT_TYPES.items():
    if info[1] != '':
        event_d[formal] = '{} ({})'.format(info[0], info[1])
    else:
        event_d[formal] = '{}'.format(info[0])
event_choices = [(et, event_d[et]) for et in sorted(event_d.keys())]


class ManualReadingForm(Form):
    fc = FloatField('Free Chlorine',
                    [Optional(), NumberRange(min=0, max=30)])
    tc = FloatField('Total Chlorine',
                    [Optional(), NumberRange(min=0, max=30)])
    ph = FloatField('pH',
                    [Optional(), NumberRange(min=2, max=10)])
    ta = IntegerField('Total Alkilinity',
                      [Optional(), NumberRange(min=10, max=300)])
    ca = IntegerField('Calcium Hardness',
                      [Optional(), NumberRange(min=10, max=300)])
    cya = IntegerField('CYA',
                       [Optional(), NumberRange(min=0, max=1000)])
    event_type = SelectField('Event',
                             [Optional()],
                             choices=event_choices)
    event_quantity = FloatField(
        'Event Quantity', [Optional(), NumberRange(min=0, max=100)])
    event_comment = StringField('Event Comment', [Optional()])
    when = DateTimeField('When',
                         [DataRequired()],
                         format='%Y-%m-%d %H:%M')


class SettingsForm(Form):
    comp_delta = IntegerField('Compensation Delta',
                              [Optional(), NumberRange(min=1, max=30)])
    reading_interval = IntegerField('Reading Interval',
                                    [Optional(), NumberRange(min=0, max=3600)])
