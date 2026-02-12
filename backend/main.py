import math
from typing import List, Tuple

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware


def _decode_polyline(polyline_str: str, precision: int = 5) -> List[Tuple[float, float]]:
    """
    Decode a polyline string (encoded by Google's polyline algorithm).
    Returns list of (lat, lng) tuples.
    """
    inv = 1.0 / (10 ** precision)
    decoded = []
    previous = [0, 0]
    i = 0
    
    while i < len(polyline_str):
        ll = [0, 0]
        for j in [0, 1]:
            shift = 0
            result = 0
            while True:
                byte_val = ord(polyline_str[i]) - 63
                i += 1
                result |= (byte_val & 0x1f) << shift
                shift += 5
                if not (byte_val & 0x20):
                    break
            
            if result & 1:
                ll[j] = previous[j] + ~(result >> 1)
            else:
                ll[j] = previous[j] + (result >> 1)
            previous[j] = ll[j]
        
        decoded.append((ll[0] * inv, ll[1] * inv))
    
    return decoded

from backend.config import ORS_API_KEY, ORS_BASE_URL
from backend.models import (
    RouteRequest,
    RoutesResponse,
    RouteResponseItem,
    RouteSegment,
)
from backend.flood_risk import (
    compute_route_risk,
    generate_heatmap_points,
    compute_bad_road_penalty_along_route,
)

app = FastAPI(title="OptiRoute Backend", version="0.1.0")

# CORS: allow frontend dev server on localhost:5173, adjust as needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _to_coordinates_list(ors_coords: List[List[float]]) -> List[RouteSegment]:
    # ORS returns [lng, lat]
    return [RouteSegment(lat=lat, lng=lng) for lng, lat in ors_coords]


async def geocode_destination(text: str) -> Tuple[float, float]:
    """
    Use OpenRouteService Geocoding API to resolve a text address in Mumbai to lat/lng.
    For demo purposes; in production you'd handle errors, multiple results, etc.
    """
    if not ORS_API_KEY:
        raise HTTPException(status_code=500, detail="ORS_API_KEY not configured")

    url = f"{ORS_BASE_URL}/geocode/search"
    
    # Append ", Mumbai" to the search to force results in Mumbai
    search_text = text if ", Mumbai" in text.lower() or ", india" in text.lower() else f"{text}, Mumbai"
    
    params = {
        "api_key": ORS_API_KEY,
        "text": search_text,
        "size": 1,
        "boundary.circle.lon": 72.8777,  # approximate Mumbai center
        "boundary.circle.lat": 19.0760,
        "boundary.circle.radius": 30_000,  # meters
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)
        if resp.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"Geocoding failed: {resp.text}",
            )
        data = resp.json()
        features = data.get("features") or []
        if not features:
            raise HTTPException(status_code=404, detail="Destination not found in Mumbai")
        coords = features[0]["geometry"]["coordinates"]  # [lon, lat]
        dest_lat, dest_lng = coords[1], coords[0]
        
        # Stricter bounds: must be within Mumbai city area
        # Mumbai city boundaries are approximately:
        # North: 19.26°N, South: 18.96°N, East: 73.02°E, West: 72.80°E
        mumbai_lat_min, mumbai_lat_max = 18.90, 19.30
        mumbai_lng_min, mumbai_lng_max = 72.75, 73.10
        
        print(f"[GEOCODING] '{text}' (searched as '{search_text}') → lat={dest_lat:.4f}, lng={dest_lng:.4f}")
        
        if not (mumbai_lat_min <= dest_lat <= mumbai_lat_max and 
                mumbai_lng_min <= dest_lng <= mumbai_lng_max):
            raise HTTPException(
                status_code=404,
                detail=f"'{text}' geocoded to lat={dest_lat:.2f}, lng={dest_lng:.2f} which is outside Mumbai. Got: {features[0]}"
            )
        
        return dest_lat, dest_lng


async def fetch_route(
    profile: str,
    origin: Tuple[float, float],
    destination: Tuple[float, float],
    avoid_polygons_geojson: dict | None = None,
) -> Tuple[List[RouteSegment], float, float]:
    """
    Call ORS Directions API for a single route.
    """
    if not ORS_API_KEY:
        raise HTTPException(status_code=500, detail="ORS_API_KEY not configured")

    # Validate coordinates are within reasonable range (sanity check before routing)
    def is_valid_mumbai_coord(lat: float, lng: float) -> bool:
        # Mumbai metro area bounds with generous margins
        return (18.5 <= lat <= 19.5 and 72.3 <= lng <= 73.5)
    
    if not is_valid_mumbai_coord(origin[0], origin[1]):
        raise HTTPException(
            status_code=400,
            detail=f"Origin {origin} is outside Mumbai area"
        )
    if not is_valid_mumbai_coord(destination[0], destination[1]):
        raise HTTPException(
            status_code=400,
            detail=f"Destination {destination} is outside Mumbai area"
        )
    
    # Sanity check: max distance between two points in Mumbai should be ~60 km
    # If greater, something went wrong with geocoding
    dist_degrees = ((destination[0] - origin[0])**2 + (destination[1] - origin[1])**2) ** 0.5
    if dist_degrees > 0.7:  # ~77 km at this latitude, but should flag as suspicious
        raise HTTPException(
            status_code=400,
            detail="Route distance seems too large. Please check your destination and try again."
        )
    
    print(f"[ROUTING] Origin: {origin}, Destination: {destination}, Distance: {dist_degrees:.4f}°")

    url = f"{ORS_BASE_URL}/v2/directions/{profile}"
    body: dict = {
    "coordinates": [
        [origin[1], origin[0]],
        [destination[1], destination[0]],
    ],
    "format": "geojson"
}


    if avoid_polygons_geojson:
        body.setdefault("options", {})
        body["options"]["avoid_polygons"] = avoid_polygons_geojson

    headers = {"Authorization": ORS_API_KEY, "Content-Type": "application/json"}
    
    print(f"[ORS_REQUEST] {profile}: {origin} → {destination}")
    print(f"[ORS_BODY] {body}")

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(url, json=body, headers=headers)
        if resp.status_code != 200:
            # Parse error response for better messaging
            try:
                error_data = resp.json()
                error_msg = error_data.get("error", {})
                if isinstance(error_msg, dict):
                    error_detail = error_msg.get("message", str(error_msg))
                else:
                    error_detail = str(error_msg)
                    
                if "routable point" in error_detail.lower():
                    raise HTTPException(
                        status_code=400,
                        detail="Route endpoint is not accessible by road. Try a different destination."
                    )
                elif "exceed" in error_detail.lower() and "distance" in error_detail.lower():
                    raise HTTPException(
                        status_code=400,
                        detail="Route is too long. Please choose destinations closer together in Mumbai."
                    )
            except HTTPException:
                raise
            except:
                pass
            raise HTTPException(
                status_code=500, detail=f"Routing failed: {resp.text}"
            )
        data = resp.json()
        
        # Better error diagnostics
        if "error" in data:
            error_msg = data.get("error", {})
            if isinstance(error_msg, dict):
                error_msg = error_msg.get("message", str(error_msg))
            raise HTTPException(
                status_code=400, detail=f"ORS API error: {error_msg}"
            )
        
        routes = data.get("routes") or []
        if not routes:
            raise HTTPException(
                status_code=400,
                detail="No route found from ORS API"
            )

        route = routes[0]
        summary = route["summary"]
        distance_m = summary["distance"]
        duration_s = summary["duration"]

        # Decode polyline geometry
        geometry_str = route.get("geometry", "")
        if not geometry_str:
            raise HTTPException(
                status_code=500,
                detail="Route has no geometry data"
            )
        
        # geometry is encoded polyline: decode it to (lat, lng) tuples
        decoded_coords = _decode_polyline(geometry_str)
        segments = [RouteSegment(lat=lat, lng=lng) for lat, lng in decoded_coords]

        return segments, distance_m, duration_s


async def fetch_rainfall_mm_near_mumbai() -> List[Tuple[float, float, float]]:
    """
    Open-Meteo: free, no API key. Returns rainfall grid for Mumbai.
    """
    center_lat, center_lng = 19.0760, 72.8777

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": center_lat,
        "longitude": center_lng,
        "hourly": "precipitation",
        "past_hours": 24,
        "forecast_hours": 0,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)
        if resp.status_code != 200:
            return []

        data = resp.json()
        hourly = data.get("hourly") or {}
        precip = hourly.get("precipitation") or []

    total_rain = sum(float(p or 0) for p in precip[:24])

    # Build grid (same format as before)
    offsets = [
        (0.0, 0.0),
        (0.03, 0.03),
        (0.03, -0.03),
        (-0.03, 0.03),
        (-0.03, -0.03),
    ]
    return [
        (center_lat + dlat, center_lng + dlng, total_rain)
        for dlat, dlng in offsets
    ]


def _sample_route_for_rain(coordinates: List[RouteSegment], max_points: int = 100) -> List[RouteSegment]:
    """
    Smart down-sampling of route coordinates for risk/rainfall computation.
    Ensures we have enough points to accurately assess flood risk along the route.
    """
    if len(coordinates) <= max_points:
        return coordinates
    step = max(1, len(coordinates) // max_points)
    return coordinates[::step]


def _assign_rain_to_route(
    sampled_coords: List[RouteSegment],
    rainfall_grid: List[Tuple[float, float, float]],
) -> List[float]:
    """
    Assign rainfall to each point along the route.
    Uses nearest-neighbor in the rainfall grid for simplicity.
    """
    if not rainfall_grid:
        return [0.0 for _ in sampled_coords]

    def haversine(lat1, lon1, lat2, lon2) -> float:
        R = 6371000.0
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(
            dlambda / 2
        ) ** 2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    rains: List[float] = []
    for coord in sampled_coords:
        best_rain = 0.0
        best_dist = float("inf")
        for lat, lng, rain_mm in rainfall_grid:
            d = haversine(coord.lat, coord.lng, lat, lng)
            if d < best_dist:
                best_dist = d
                best_rain = rain_mm
        rains.append(best_rain)
    return rains


def _make_avoid_polygon_smart(scale: float) -> dict:
    """
    Create an avoidance polygon centered on high-risk waterlogging areas.
    
    This polygon is used by ORS to push routes away from the most flood-prone zones.
    As scale increases, the avoidance area expands to force safer routes.
    
    ORS limit: polygon area must not exceed 200 square km (2.0E8 square meters)
    
    - scale=0.5: Light avoidance, routes mostly unaffected but avoid worst hotspots
    - scale=1.0: Strong avoidance, forces routes away from known flood areas
    """
    # Center on high-density waterlogging area (central Mumbai)
    center_lat, center_lng = 19.0760, 72.8777
    # Scale in degrees; max safe d ≈ 0.045 degrees to stay under 200 sq km
    # Using smaller base to be safe: 0.03° ≈ 3.3 km
    d = 0.03 * scale

    coords = [
        [center_lng - d, center_lat - d],
        [center_lng + d, center_lat - d],
        [center_lng + d, center_lat + d],
        [center_lng - d, center_lat + d],
        [center_lng - d, center_lat - d],
    ]
    return {
        "type": "Polygon",
        "coordinates": [coords],
    }


@app.post("/api/routes", response_model=RoutesResponse)
async def get_routes(payload: RouteRequest) -> RoutesResponse:
    """
    Two-Layer Risk-Aware Routing:
    
    1. Static Layer: Precomputed waterlogging preference map (inherent vulnerability)
    2. Dynamic Layer: Real-time rainfall modulation (current weather activation)
    
    Returns three route options:
    - Fastest: Minimum distance
    - Balanced: Balanced distance vs. flood risk tradeoff
    - Safest: Minimum flood risk with acceptable distance
    """
    if not payload.origin:
        raise HTTPException(status_code=400, detail="origin is required")
    
    # Validate origin coordinates
    if payload.origin.lat == 0 and payload.origin.lng == 0:
        raise HTTPException(
            status_code=400,
            detail="Invalid origin coordinates (0, 0). Please enable location access and try again."
        )
    if not (-90 <= payload.origin.lat <= 90 and -180 <= payload.origin.lng <= 180):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid origin coordinates: {payload.origin.lat}, {payload.origin.lng}"
        )

    origin = (payload.origin.lat, payload.origin.lng)

    if payload.destination:
        dest = (payload.destination.lat, payload.destination.lng)
    elif payload.destination_text:
        dest = await geocode_destination(payload.destination_text)
    else:
        raise HTTPException(
            status_code=400,
            detail="Either destination or destination_text is required",
        )
    
    print(f"[API_REQUEST] Origin: {origin}, Destination text: {payload.destination_text}, Dest coords: {dest}")

    # Fetch rainfall grid once (applies to all routes equally)
    rainfall_grid = await fetch_rainfall_mm_near_mumbai()

    # Generate routes using different strategies
    # =========================================

    # Route 1: Fastest (baseline, no avoidance)
    fastest_coords, fastest_dist, fastest_dur = await fetch_route(
        profile="driving-car",
        origin=origin,
        destination=dest,
    )

    # Routes 2 & 3: Safer/Safest by progressively increasing avoidance
    # These routes actively avoid known flood-prone areas from the preference map
    safer_coords, safer_dist, safer_dur = await fetch_route(
        profile="driving-car",
        origin=origin,
        destination=dest,
        avoid_polygons_geojson=_make_avoid_polygon_smart(scale=0.5),
    )

    safest_coords, safest_dist, safest_dur = await fetch_route(
        profile="driving-car",
        origin=origin,
        destination=dest,
        avoid_polygons_geojson=_make_avoid_polygon_smart(scale=1.0),
    )

    # Compute risk scores and bad-road penalties using the two-layer system
    # ====================================================================
    all_routes_coords = [fastest_coords, safer_coords, safest_coords]
    sampled_routes: List[List[RouteSegment]] = []
    rain_alongs: List[List[float]] = []
    risk_scores: List[float] = []
    bad_penalties: List[float] = []

    for coords in all_routes_coords:
        sampled = _sample_route_for_rain(coords)
        rain_along = _assign_rain_to_route(sampled, rainfall_grid)
        risk = compute_route_risk(sampled, rain_along)
        bad = compute_bad_road_penalty_along_route(sampled)

        sampled_routes.append(sampled)
        rain_alongs.append(rain_along)
        risk_scores.append(risk)
        bad_penalties.append(bad)

    fastest_risk, safer_risk, safest_risk = risk_scores
    fastest_bad, safer_bad, safest_bad = bad_penalties

    # Combine into a single score for ranking/explanation
    dists = [fastest_dist, safer_dist, safest_dist]
    min_d, max_d = min(dists), max(dists)
    dist_range = max(max_d - min_d, 1.0)

    combined_scores: List[float] = []
    for idx, (r, b, dist) in enumerate(zip(risk_scores, bad_penalties, dists)):
        dist_norm = (dist - min_d) / dist_range
        # weights: risk 60%, bad-road 30%, distance 10%
        score = 0.6 * r + 0.3 * b + 0.1 * dist_norm
        combined_scores.append(score)

    # Build response: three meaningful route options
    routes = [
        RouteResponseItem(
            id="fastest",
            label="Fastest Route",
            color="#1E88E5",  # Blue
            distance_m=fastest_dist,
            duration_s=fastest_dur,
            risk_score=fastest_risk,
            score=combined_scores[0],
            explanation="",
            coordinates=fastest_coords,
        ),
        RouteResponseItem(
            id="safer",
            label="Balanced Route",
            color="#43A047",  # Green
            distance_m=safer_dist,
            duration_s=safer_dur,
            risk_score=safer_risk,
            score=combined_scores[1],
            explanation="",
            coordinates=safer_coords,
        ),
        RouteResponseItem(
            id="safest",
            label="Safest Route",
            color="#F4511E",  # Orange
            distance_m=safest_dist,
            duration_s=safest_dur,
            risk_score=safest_risk,
            score=combined_scores[2],
            explanation="",
            coordinates=safest_coords,
        ),
    ]

    # Generate heatmap showing the preference map + rainfall modulation
    heatmap_points = generate_heatmap_points(all_routes_coords, rainfall_grid)

    # Build explanations comparing to fastest route
    fastest_idx = 0
    min_dist = min(fastest_dist, safer_dist, safest_dist)
    for idx, item in enumerate(routes):
        parts: List[str] = []
        # distance comparison
        rel_pct = ((item.distance_m - min_dist) / max(min_dist, 1.0)) * 100.0
        if rel_pct <= 1.0:
            parts.append("Shortest distance")
        else:
            parts.append(f"{rel_pct:.0f}% longer than shortest route")

        # risk explanation
        r = [fastest_risk, safer_risk, safest_risk][idx]
        parts.append(f"Flood risk: {(r * 100):.0f}%")

        # bad road note
        b = [fastest_bad, safer_bad, safest_bad][idx]
        if b > 0.4:
            parts.append("Passes near known poor road conditions — expect delays or rough patches")
        elif b > 0.1:
            parts.append("Minor poor-road segments noted")

        # final advice
        if idx == 0:
            parts.append("Good balance of speed")
        else:
            parts.append("Safer routing avoids hotspots")

        item.explanation = "; ".join(parts)

    return RoutesResponse(routes=routes, heatmap_points=heatmap_points)


@app.get("/api/heatmap")
async def get_heatmap_data():
    """
    Returns heatmap showing flood risk based on live rainfall and waterlogging data.
    Independent endpoint for fetching heatmap without requiring a route search.
    """
    # Fetch real-time rainfall data
    rainfall_grid = await fetch_rainfall_mm_near_mumbai()
    
    # Generate heatmap points based on current rainfall and waterlogging preference map
    heatmap_points = generate_heatmap_points([], rainfall_grid)
    
    return {"heatmap_points": heatmap_points}