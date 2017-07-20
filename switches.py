'''
Gets info and controls switches for the pool
'''

switch_states = {
    'overhead': 'on',
    'pool': 'off',
    'spa': 'off'
}


def get_switch_states():
    '''Gets the current switch states'''
    return switch_states


def set_switch(name, state):
    '''Sets a switch on or off'''
    if name not in switch_states:
        raise KeyError('unknown switch name')
    if state != 'on' and state != 'off':
        raise ValueError('state must be either on or off')
    switch_states[name] = state
