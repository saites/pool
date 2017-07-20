'''
Communicates with the sensors to obtain readings
'''
import random


def get_pH():
    '''Returns current pH value.
    note that value is adjusted by sensor probe based on temperature.
    To update this value, use set_pH_temp_compensation.
    '''
    return random.random() * .5 + 7


def set_pH_temp_compensation(temperature):
    '''Sets the pH probe's temperature compensation.
    Specify temperature in degrees Celcius.
    '''
    pass


def get_water_temperature():
    '''Returns current water temperature in degrees C.'''
    return random.randint(20, 30)


def get_air_temperature():
    '''Returns current air temperature in degrees C.'''
    return random.randint(30, 38)


def get_internal_temperature():
    '''Returns the current temperature of the Pi'''
    return random.randint(40, 50)
