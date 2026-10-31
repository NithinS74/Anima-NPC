"""Small topology/offset checks for the optional offline Blender conversion."""

import math

NATIVE_MORPHS = ("BlinkLeft", "BlinkRight", "Aah", "Oh", "BMP", "MoodHappy", "MoodAnger", "MoodFear")


def matching_topology(vertex_count, polygons, base_vertices, faces):
    if not 1 <= vertex_count <= 5000 or vertex_count != len(base_vertices):
        return False
    if not faces or len(polygons) != len(faces) or len(faces) > 10000:
        return False
    if any(len(face) != 3 or any(type(i) is not int or not 0 <= i < vertex_count for i in face)
           for face in [*polygons, *faces]):
        return False
    canonical = lambda items: sorted(tuple(sorted(face)) for face in items)
    return canonical(polygons) == canonical(faces)


def morph_offsets(base, target):
    if not 1 <= len(base) == len(target) <= 5000:
        raise ValueError("morph vertex count mismatch")
    result = []
    for original, moved in zip(base, target):
        if len(original) != 3 or len(moved) != 3:
            raise ValueError("invalid morph coordinate")
        delta = tuple(float(b) - float(a) for a, b in zip(original, moved))
        if any(not math.isfinite(value) or abs(value) > 25 for value in delta):
            raise ValueError("invalid morph displacement")
        result.append(delta)
    return result
