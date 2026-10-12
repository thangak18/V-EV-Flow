"""Great-circle distance with a fixed road-winding factor (no routing service)."""

import math

from app.backend.contracts.common import Coordinate

EARTH_RADIUS_KM = 6371.0
ROAD_FACTOR = 1.3  # assumption: road distance is 30% longer than the straight line


def haversine_km(a: Coordinate, b: Coordinate) -> float:
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    dlat = lat2 - lat1
    dlng = math.radians(b.lng - a.lng)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(h))


def road_km(a: Coordinate, b: Coordinate) -> float:
    return ROAD_FACTOR * haversine_km(a, b)
