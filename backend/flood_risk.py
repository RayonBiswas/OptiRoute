"""
Two-Layer Flood Risk System:

Layer 1: Static Waterlogging Preference Map
  - Computed once from known flood pivots
  - Uses exponential distance decay: W(x) = max over pivots of ( severity × exp(-distance / σ) )
  - Represents inherent flood vulnerability of the city

Layer 2: Real-Time Rainfall Modulation
  - Multiplies preference map by rainfall factor
  - Final risk: R(x, t) = Preference(x) × RainFactor(t)
  - Rain activates existing vulnerabilities
"""

import csv
import math
from pathlib import Path
from typing import List, Tuple

from .models import RouteSegment, HeatmapPoint

# Optional static bad-road data (points with severity) - file: backend/data/bad_roads.csv
BAD_ROADS_PATH = Path(__file__).resolve().parent / "data" / "bad_roads.csv"


def _load_bad_roads() -> List[Tuple[float, float, float]]:
    """Returns list of (lat, lon, severity) for known bad roads."""
    items: List[Tuple[float, float, float]] = []
    if not BAD_ROADS_PATH.exists():
        # fallback sample bad roads
        return [
            (19.0757, 72.8772, 0.6),  # near CST
            (19.0600, 72.8850, 0.7),
            (19.0400, 72.8400, 0.5),
        ]
    with open(BAD_ROADS_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            items.append((float(row["lat"]), float(row["lon"]), float(row.get("severity", 0.5))))
    return items


_BAD_ROADS = _load_bad_roads()


def _road_condition_at_point(lat: float, lon: float) -> float:
    """Return a penalty in [0,1] for bad road conditions near the point.

    Uses nearest bad-road point with exponential decay by distance (km).
    """
    best = 0.0
    for b_lat, b_lon, severity in _BAD_ROADS:
        d = _haversine_km(lat, lon, b_lat, b_lon)
        influence = math.exp(-d / 1.0)  # 1 km decay
        best = max(best, severity * influence)
    return min(best, 1.0)


def compute_bad_road_penalty_along_route(coordinates: List[RouteSegment]) -> float:
    """Compute average bad-road penalty along a route (0..1)."""
    if not coordinates:
        return 0.0
    total = 0.0
    for c in coordinates:
        total += _road_condition_at_point(c.lat, c.lng)
    return total / len(coordinates)


# Load true flood pivots from CSV (anchor points)
PIVOTS_PATH = Path(__file__).resolve().parent / "data" / "flood_pivots.csv"

# Spread factor: higher = faster decay (risk spreads less far)
SPREAD_FACTOR_KM = 2.0

def _load_pivots() -> List[Tuple[float, float, float]]:
    """Returns list of (lat, lon, severity)."""
    pivots: List[Tuple[float, float, float]] = []
    if not PIVOTS_PATH.exists():
        # Fallback if CSV missing
        return [
            (19.0056, 72.8417, 0.95),   # Hindmata
            (19.1197, 72.8464, 0.90),  # Andheri Subway
            (19.0286, 72.8553, 0.88),  # Kings Circle
            (19.0728, 72.8826, 0.85),  # Kurla
        ]
    with open(PIVOTS_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pivots.append((
                float(row["lat"]),
                float(row["lon"]),
                float(row["severity"]),
            ))
    return pivots

_FLOOD_PIVOTS = _load_pivots()


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute distance in km between two lat/lon points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _preference_map_at_point(lat: float, lon: float) -> float:
    """
    Layer 1: Static Waterlogging Preference Map
    
    For any location (lat, lon), compute the maximum weighted influence from all pivots.
    
    Formula: Preference(x) = max over all pivots i of:
        severity_i × exp( - distance(x, pivot_i) / σ )
    
    Where σ = SPREAD_FACTOR_KM (how fast risk decays with distance)
    
    Result: [0, 1] where 1 = maximum flood-prone, 0 = no inherent risk
    """
    preference = 0.0
    
    for p_lat, p_lon, severity in _FLOOD_PIVOTS:
        distance_km = _haversine_km(lat, lon, p_lat, p_lon)
        # Exponential decay: closer points have exponentially more influence
        spatial_influence = math.exp(-distance_km / SPREAD_FACTOR_KM)
        contribution = severity * spatial_influence
        preference = max(preference, contribution)
    
    return min(preference, 1.0)


def _rainfall_factor(rainfall_24h_mm: float) -> float:
    """
    Layer 2: Rainfall Modulation Factor
    
    Maps real-time rainfall intensity to [0, 1] multiplier.
    - 0 mm rain → factor = 0.1 (base vulnerability still visible)
    - 20 mm rain → factor ≈ 0.5
    - 100+ mm rain → factor = 1.0 (full risk activation)
    
    This is a sigmoid-like mapping: non-linear but smooth.
    """
    if rainfall_24h_mm <= 0:
        return 0.1  # base level, always some structural risk
    # Normalized by 100mm as reference (heavy rain threshold)
    normalized = min(rainfall_24h_mm / 100.0, 1.0)
    # Smooth ramping: softer than linear, avoids false positives in dry weather
    return 0.1 + 0.9 * (normalized ** 0.6)


def flood_risk_at_point(lat: float, lon: float, rainfall_24h_mm: float) -> float:
    """
    Combined Risk = Preference Map × Rainfall Factor
    
    This is the final risk at a single point:
    - Preference map encodes structural/geographical vulnerability
    - Rainfall factor modulates based on current weather
    - Non-zero even with no rain (preserves known hotspots)
    """
    preference = _preference_map_at_point(lat, lon)
    rain_factor = _rainfall_factor(rainfall_24h_mm)
    return preference * rain_factor


def point_in_hotspot(lat: float, lng: float) -> float:
    """Preference map without rainfall modulation (structural vulnerability)."""
    return _preference_map_at_point(lat, lng)


def compute_route_risk(
    coordinates: List[RouteSegment],
    rainfall_mm_along_route: List[float],
) -> float:
    """
    Average risk along entire route.
    
    Samples the route at discrete points and computes mean final risk.
    """
    if not coordinates or not rainfall_mm_along_route:
        return 0.0

    n = min(len(coordinates), len(rainfall_mm_along_route))
    total = 0.0
    for i in range(n):
        r = flood_risk_at_point(
            coordinates[i].lat,
            coordinates[i].lng,
            rainfall_mm_along_route[i],
        )
        total += r
    return total / float(n)


def generate_heatmap_points(
    routes_coordinates: List[List[RouteSegment]],
    rainfall_grid_points: List[Tuple[float, float, float]],
) -> List[HeatmapPoint]:
    """
    Generate dense grid of heatmap points over Mumbai.
    
    Uses preference map × rainfall factor to show current risk landscape.
    Only includes points with meaningful risk (intensity > 0.05).
    """
    # Get total rainfall from grid
    rainfall_24h = 0.0
    if rainfall_grid_points:
        rainfall_24h = sum(p[2] for p in rainfall_grid_points) / max(len(rainfall_grid_points), 1)

    heatmap: List[HeatmapPoint] = []
    # Mumbai bounding box: ~0.015° step ~1.6km apart
    for lat in [18.90 + i * 0.015 for i in range(35)]:
        for lon in [72.75 + j * 0.015 for j in range(35)]:
            risk = flood_risk_at_point(lat, lon, rainfall_24h)
            if risk > 0.05:  # Only show meaningful risk
                heatmap.append(HeatmapPoint(lat=lat, lng=lon, intensity=risk))

    return heatmap