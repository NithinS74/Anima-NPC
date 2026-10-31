import math

import pytest

from tools.npc_lab.face_import import matching_topology, morph_offsets


def test_facial_topology_requires_equal_vertex_order_connectivity():
    base = [(0, 0, 0)] * 4
    assert matching_topology(4, [(0, 1, 2), (1, 2, 3)], base, [(3, 2, 1), (2, 1, 0)])
    assert not matching_topology(4, [(0, 1, 2)], base, [(0, 1, 3)])
    assert not matching_topology(5, [(0, 1, 2)], base, [(0, 1, 2)])
    assert not matching_topology(4, [(-1, 1, 2)], base, [(-1, 1, 2)])
    assert not matching_topology(4, [], base, [])


def test_native_morph_delta_retains_the_specific_character_face():
    base = [(1, 2, 3), (4, 5, 6)]
    target = [(1, 2, 3.5), (4.1, 5, 6)]
    deltas = morph_offsets(base, target)
    custom_face = [(10, 20, 30), (40, 50, 60)]
    applied = [tuple(x + d for x, d in zip(vertex, delta)) for vertex, delta in zip(custom_face, deltas)]
    assert applied[0] == (10, 20, 30.5)
    assert applied[1] == pytest.approx((40.1, 50, 60))


@pytest.mark.parametrize("target", [[], [(math.nan, 0, 0)], [(30, 0, 0)], [(0, 1)]])
def test_invalid_morphs_fail_without_corrupting_geometry(target):
    with pytest.raises(ValueError): morph_offsets([(0, 0, 0)], target)
