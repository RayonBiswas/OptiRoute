# OptiRoute Implementation Reference

## 📁 Key Files

### [backend/flood_risk.py](backend/flood_risk.py)
**Core risk computation logic**

#### Functions

| Function | Purpose | Returns |
|----------|---------|---------|
| `_load_pivots()` | Read waterlogging anchors from CSV | `List[Tuple[lat, lon, severity]]` |
| `_preference_map_at_point(lat, lon)` | **Layer 1**: Static structural vulnerability | `float [0, 1]` |
| `_rainfall_factor(rainfall_mm)` | **Layer 2**: Weather modulation multiplier | `float [0.1, 1.0]` |
| `flood_risk_at_point(lat, lon, rainfall_mm)` | **Combined risk** = Preference × RainFactor | `float [0, 1]` |
| `point_in_hotspot(lat, lng)` | Preference map alone (no weather) | `float [0, 1]` |
| `compute_route_risk(coords, rainfall_list)` | Average risk across an entire route | `float [0, 1]` |
| `generate_heatmap_points(routes, rainfall_grid)` | Dense grid for visualization | `List[HeatmapPoint]` |

**Key Constants:**
```python
SPREAD_FACTOR_KM = 2.0  # How fast distance decay spreads
```

---

### [backend/main.py](backend/main.py)
**FastAPI server & route generation**

#### Functions

| Function | Purpose |
|----------|---------|
| `geocode_destination(text)` | Convert "Bandra" → lat/lng via ORS |
| `fetch_route(profile, origin, dest, avoid_polygons)` | Call ORS Directions API |
| `fetch_rainfall_mm_near_mumbai()` | Get 24h rainfall from Open-Meteo |
| `_sample_route_for_rain(coords, max_points)` | Down-sample route for efficiency |
| `_assign_rain_to_route(coords, rainfall_grid)` | Map rainfall to each route point |
| `_make_avoid_polygon_smart(scale)` | Create GeoJSON polygon for ORS avoidance |
| `get_routes(payload)` | **Main endpoint** – returns 3 routes + heatmap |

#### Endpoint
```
POST /api/routes
```

**Request Model:** [RouteRequest](backend/models.py#L5)  
**Response Model:** [RoutesResponse](backend/models.py#L31)

---

### [backend/data/flood_pivots.csv](backend/data/flood_pivots.csv)
**Waterlogging ground truth**

**Columns:**
- `lat`, `lon`: Coordinates
- `severity`: Historical flood frequency (0–1, higher = more frequent)
- `name`: Location name (for reference)

**15 known hotspots** covering Mumbai:
- Central: Hindmata (0.95), Kings Circle (0.88), Dadar (0.78)
- East: Kurla (0.85), Parel (0.72)
- North: Andheri Subway (0.90), Borivali (0.75)
- West: Mahim (0.82), Colaba (0.60)
- Islands: Powai (0.68), Mulund (0.70)

---

## 🔄 Request → Response Flow

```
1. User calls POST /api/routes
   └─ Origin + Destination (text or coords)

2. get_routes() endpoint
   ├─ Geocode destination if needed
   ├─ Fetch rainfall grid (Open-Meteo)
   │
   ├─ Generate 3 routes via ORS:
   │  ├─ Fastest (no avoidance)
   │  ├─ Balanced (light polygon avoidance)
   │  └─ Safest (strong polygon avoidance)
   │
   ├─ Score each route:
   │  ├─ Sample 100 points along path
   │  ├─ Get rainfall at each point
   │  ├─ Compute risk via flood_risk_at_point()
   │  └─ Average to get route_risk_score
   │
   ├─ Generate heatmap:
   │  ├─ Dense grid over Mumbai (~1.6 km spacing)
   │  └─ Risk at each grid point via flood_risk_at_point()
   │
   └─ Return RoutesResponse
       ├─ routes[0]: Fastest
       ├─ routes[1]: Balanced
       ├─ routes[2]: Safest
       └─ heatmap_points[]
```

---

## 🧮 Core Equations (Ready-to-Explain)

### Preference Map (Structural Risk)
$$P(x) = \max_i \left( s_i \cdot e^{-d(x, p_i) / 2.0} \right)$$

- $P(x)$ = how flood-prone is location x structurally
- $s_i$ = severity of pivot i (from CSV)
- $d(x, p_i)$ = km distance from x to pivot i
- 2.0 = spread factor (decay rate)

### Rainfall Factor (Weather Modulation)
$$R(r) = \begin{cases}
0.1 & \text{if } r = 0 \\
0.1 + 0.9 \cdot (r/100)^{0.6} & \text{if } r > 0
\end{cases}$$

- $R(r)$ = how much rainfall amplifies risk
- $r$ = 24-hour rainfall in mm
- 0.1 = minimum (structural risk always visible)
- 1.0 = maximum (heavy rain := 100+ mm)

### Final Risk
$$\text{Risk}(x, t) = P(x) \cdot R(\text{rainfall}(t))$$

---

## 🧪 Testing Locally

### Test the preference map:
```bash
cd backend
python -c "
from flood_risk import _preference_map_at_point, flood_risk_at_point
import json

# Dry weather
risk_dry = flood_risk_at_point(19.0056, 72.8417, 0.0)
print(f'Hindmata (dry): {risk_dry:.3f}')

# Heavy rain
risk_wet = flood_risk_at_point(19.0056, 72.8417, 100.0)
print(f'Hindmata (100mm): {risk_wet:.3f}')

# Structural only
pref = _preference_map_at_point(19.0056, 72.8417)
print(f'Preference: {pref:.3f}')
"
```

### Start the server:
```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

### Call the endpoint:
```bash
curl -X POST http://localhost:8000/api/routes \
  -H "Content-Type: application/json" \
  -d '{
    "origin": {"lat": 19.0760, "lng": 72.8777},
    "destination_text": "Bandra Kurla Complex"
  }'
```

---

## 🎯 Configuration

### [backend/config.py](backend/config.py)

**Required environment variables:**
```bash
ORS_API_KEY=your_key_here      # OpenRouteService Directions API
ORS_BASE_URL=https://api.openrouteservice.org  # Usually default
APP_HOST=127.0.0.1
APP_PORT=8000
```

**⚠️ Note:** Open-Meteo (rainfall) is free, no key needed.

---

## 📊 Data Flow (Detailed)

### Preference Map Computation (Offline)
```
CSV (flood_pivots.csv) → _load_pivots()
                  ↓
            _FLOOD_PIVOTS list (in-memory cache)
                  ↓
           _preference_map_at_point(lat, lon)
                  ↓
           Latest: Preference ∈ [0, 1]
```

### Real-Time Risk Computation (Online)
```
Request → Origin + Destination
   ↓
fetch_rainfall_mm_near_mumbai()
   ├─ Open-Meteo API call
   ├─ Parse 24h precipitation
   └─ rainfall_grid: List[(lat, lon, mm)]
   ↓
For each route coordinate:
   ├─ Preference = _preference_map_at_point(lat, lon)
   ├─ Rain factor = _rainfall_factor(rainfall_mm)
   ├─ Risk = Preference × Rain factor
   └─ Repeat, average for route_risk
   ↓
Response: [fastest, balanced, safest] + heatmap
```

---

## 🔧 Tuning Parameters

### To make routes AVOID floods more aggressively:
Edit in [backend/main.py](backend/main.py):
```python
# Currently:
_make_avoid_polygon_smart(scale=0.8)   # Safer
_make_avoid_polygon_smart(scale=1.5)   # Safest

# More aggressive:
_make_avoid_polygon_smart(scale=1.2)   # Safer
_make_avoid_polygon_smart(scale=2.0)   # Safest
```

### To adjust how fast risk spreads from a pivot:
Edit in [backend/flood_risk.py](backend/flood_risk.py):
```python
# Currently:
SPREAD_FACTOR_KM = 2.0

# Faster decay (risk stays near pivots):
SPREAD_FACTOR_KM = 1.0  # Risk drops off in ~1 km

# Slower decay (risk spreads farther):
SPREAD_FACTOR_KM = 3.0  # Risk spreads to 3-4 km away
```

### To adjust rainfall sensitivity:
Edit in [backend/flood_risk.py](backend/flood_risk.py):
```python
# In _rainfall_factor(), the 100.0 threshold:

# More sensitive to small rain:
normalized = min(rainfall_24h_mm / 50.0, 1.0)   # 50mm = full effect

# Less sensitive, need heavy rain:
normalized = min(rainfall_24h_mm / 150.0, 1.0)  # 150mm = full effect
```

---

## 📈 Scaling Checklist

- [ ] Add more pivots to `flood_pivots.csv` as you collect more data
- [ ] Periodically update severity scores based on incident logs
- [ ] Cache preference map at startup (compute once, reuse)
- [ ] Batch heatmap generation if grid becomes huge
- [ ] Add seasonal coefficients (monsoon vs. dry season)
- [ ] Log all routing requests for A/B testing
- [ ] Validate via historical flood events ("would we have routed around it?")

---

**Last Updated:** February 2026
