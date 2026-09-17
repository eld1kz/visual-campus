"""Small geodesy helpers shared by collectors."""

import math

from shapely.geometry.base import BaseGeometry

KM_PER_DEGREE = 111.32


def distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6_371_000 * 2 * math.asin(math.sqrt(h))


def area_km2(geometry: BaseGeometry) -> float:
    lat = geometry.centroid.y
    return geometry.area * KM_PER_DEGREE**2 * math.cos(math.radians(lat))
