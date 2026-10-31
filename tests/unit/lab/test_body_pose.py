import math
import pytest
from tools.npc_lab.body_pose import relaxed_arm_direction


def test_relaxed_pose_is_symmetric_near_vertical_and_normalized():
    left, right = relaxed_arm_direction(-1), relaxed_arm_direction(1)
    assert left[0] == -right[0] and left[1:] == right[1:]
    assert math.sqrt(sum(v*v for v in left)) == pytest.approx(1)
    assert left[2] < -.98
    assert 0 < abs(left[0]) < .2  # slight clearance from the torso, not a T pose


@pytest.mark.parametrize("side", [0,2,True,float('nan')])
def test_invalid_arm_side_cannot_produce_a_pose(side):
    with pytest.raises(ValueError): relaxed_arm_direction(side)
