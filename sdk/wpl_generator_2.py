"""
Генератор маршрутных точек для трёхточечного змейкового пути.

Расширяет 3 seed-точки в змейку (snake pattern) для агро-обработки:
  P1 (начало) → P2 (конец ряда) → P3 (угол поля) → зигзаг-покрытие.
"""
from __future__ import annotations

from typing import Any, Dict, List


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def expand_three_points_to_snake_path(
    seed_points: List[Dict[str, Any]],
    *,
    num_passes: int = 3,
    cruise_alt_m: float = 50.0,
) -> List[Dict[str, float]]:
    """
    Принимает 3 точки (P1, P2, P3) и строит зигзагообразный маршрут:
      P1→P2 — первый проход,
      сдвиг к P3 — переход,
      обратно — второй проход,
      и т.д.

    Возвращает >= 4 маршрутных точек.
    """
    if len(seed_points) != 3:
        raise ValueError("need exactly 3 seed points")

    p1, p2, p3 = seed_points[0], seed_points[1], seed_points[2]
    alt_key = "alt_m" if "alt_m" in p1 else "alt"
    alt = float(p1.get(alt_key, cruise_alt_m)) or cruise_alt_m

    route: List[Dict[str, float]] = []

    for i in range(num_passes):
        t = i / max(num_passes - 1, 1)

        row_start_lat = _lerp(p1["lat"], p3["lat"], t)
        row_start_lon = _lerp(p1["lon"], p3["lon"], t)
        row_end_lat = _lerp(p2["lat"], p3["lat"], t)
        row_end_lon = _lerp(p2["lon"], p3["lon"], t)

        if i % 2 == 0:
            route.append({"lat": round(row_start_lat, 7), "lon": round(row_start_lon, 7), "alt_m": alt})
            route.append({"lat": round(row_end_lat, 7), "lon": round(row_end_lon, 7), "alt_m": alt})
        else:
            route.append({"lat": round(row_end_lat, 7), "lon": round(row_end_lon, 7), "alt_m": alt})
            route.append({"lat": round(row_start_lat, 7), "lon": round(row_start_lon, 7), "alt_m": alt})

    return route
