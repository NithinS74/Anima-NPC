"""Conservative arm direction for the optional offline bind-pose conversion."""

import math


def relaxed_arm_direction(side):
    if type(side) is not int or side not in (-1, 1):
        raise ValueError("arm side must be -1 or 1")
    vector = (side * .13, .035, -1.0)
    length = math.sqrt(sum(value * value for value in vector))
    return tuple(value / length for value in vector)
