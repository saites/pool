import math


def saturation_index(pH, temp, ca, ta, tds=320):
    '''Returns the Langelier Saturation Index from pH, water temp (*C),
    Calcium hardness, and total alkalinity, and optionally TDS (default 320).
    Values between -0.3 and +0.5 are considered normal'''
    if any([arg is None for arg in [pH, tds, temp, ca, ta]]):
        return None
    A = math.log10(tds - 1) / 10
    B = -13.12 * math.log10(temp + 273) + 34.55
    C = math.log10(ca) - 0.4
    D = math.log10(ta)
    pHs = (9.3 + A + B) - (C + D)
    return pH - pHs
