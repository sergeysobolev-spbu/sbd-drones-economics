"""
Генератор маршрутных точек для двухточечного пути (A → B).

Расширяет 2 seed-точки в полноценный полётный маршрут:
  takeoff → climb → cruise waypoints → descent → landing
"""
from __future__ import annotations

import math
from typing import Any, Dict, List


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _haversine_m(p1: Dict[str, float], p2: Dict[str, float]) -> float:
    R = 6_371_000
    lat1, lat2 = math.radians(p1["lat"]), math.radians(p2["lat"])
    dlat = lat2 - lat1
    dlon = math.radians(p2["lon"] - p1["lon"])
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def expand_two_points_to_path(
    seed_points: List[Dict[str, Any]],
    *,
    cruise_alt_m: float = 50.0,
    num_intermediates: int = 4,
) -> List[Dict[str, float]]:
    """
    Принимает 2 точки [{lat, lon, alt_m/alt}] и возвращает >= 4 маршрутных точек
    с промежуточными waypoint-ами на крейсерской высоте.
    """
    if len(seed_points) != 2:
        raise ValueError("need exactly 2 seed points")

    start, end = seed_points[0], seed_points[1]
    alt_key = "alt_m" if "alt_m" in start else "alt"
    start_alt = float(start.get(alt_key, 0))
    end_alt = float(end.get(alt_key, 0))

    route: List[Dict[str, float]] = []

    route.append({
        "lat": start["lat"],
        "lon": start["lon"],
        "alt_m": start_alt,
    })

    route.append({
        "lat": start["lat"],
        "lon": start["lon"],
        "alt_m": cruise_alt_m,
    })

    for i in range(1, num_intermediates + 1):
        t = i / (num_intermediates + 1)
        route.append({
            "lat": round(_lerp(start["lat"], end["lat"], t), 7),
            "lon": round(_lerp(start["lon"], end["lon"], t), 7),
            "alt_m": cruise_alt_m,
        })

    route.append({
        "lat": end["lat"],
        "lon": end["lon"],
        "alt_m": cruise_alt_m,
    })

    route.append({
        "lat": end["lat"],
        "lon": end["lon"],
        "alt_m": end_alt,
    })

    return route
