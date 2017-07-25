from wtforms import Form, DateTimeField, SelectField,\
    TextAreaField, StringField, IntegerField, DecimalField

from wtforms.validators import Optional, DataRequired, NumberRange


class ManualReadingForm(Form):
    fc = DecimalField('Free Chlorine',
                      [Optional(), NumberRange(min=0, max=30)])
    tc = DecimalField('Total Chlorine',
                      [Optional(), NumberRange(min=0, max=30)])
    ph = DecimalField('pH',
                      [Optional(), NumberRange(min=2, max=10)])
    ta = IntegerField('Total Alkilinity',
                      [Optional(), NumberRange(min=10, max=300)])
    ca = IntegerField('Calcium Hardness',
                      [Optional(), NumberRange(min=10, max=300)])
    cya = IntegerField('CYA',
                       [Optional(), NumberRange(min=0, max=1000)])
    event = StringField('Event',
                        [Optional()])
    comments = TextAreaField('Comments', [Optional()])
    when = DateTimeField('When',
                         [DataRequired()],
                         format='%Y-%m-%d %H:%M')
