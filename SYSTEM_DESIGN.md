# OptiRoute: Two-Layer Flood-Aware Routing System

## 🧠 Core Logic (Locked & Implemented)

You are building a **two-layer risk system**, not a flood prediction model.

---

## 🧱 Layer 1: Static Waterlogging Preference Map (Offline / Precomputed)

**What it answers:** "Which areas are inherently more flood-prone?"

### Inputs
- **Known waterlogging pivots**: Located in `backend/data/flood_pivots.csv`
  - 15+ real flood-prone locations in Mumbai (Hindmata, Kurla, Kings Circle, etc.)
  - Each has a **severity score** (0–1) based on historical frequency/impact
  - Example: Hindmata = 0.95 (very frequent), Colaba = 0.60 (occasional)

### The Math
For any location **x** in the city:

$$\text{Preference}(x) = \max_{i \in \text{pivots}} \left( \text{severity}_i \times e^{-\frac{d(x, \text{pivot}_i)}{\sigma}} \right)$$

Where:
- $d(x, \text{pivot}_i)$ = haversine distance in km
- $\sigma = 2.0$ km = **SPREAD_FACTOR_KM** (how fast risk decays)

### Key Insight
- **At a pivot**: Preference = severity (~0.95 for Hindmata)
- **2 km away**: Preference drops to ~0.6 × severity
- **5+ km away**: Preference approaches 0 (unless another pivot is closer)
- **No pivot nearby**: Preference = 0 (structurally safe)

### Result
A continuous, city-wide **preference map**:
- ✅ No ML needed
- ✅ Computed once, cached forever
- ✅ Explainable to humans (just distance decay)
- ✅ Improves as you add more pivots

---

## 🌧️ Layer 2: Real-Time Rainfall Modulation (Online / Dynamic)

**What it answers:** "How bad is it *today / now*?"

### Key Insight
Rainfall alone ≠ flooding. Rain **activates** existing vulnerabilities.

$$\text{FinalRisk}(x, t) = \text{Preference}(x) \times \text{RainFactor}(t)$$

### The Rainfall Factor

Maps real-time 24h rainfall to a modulation multiplier [0, 1]:

$$\text{RainFactor}(\text{rain\_mm}) = \begin{cases}
0.1 & \text{if rain\_mm} = 0 \\
0.1 + 0.9 \times \left(\frac{\text{rain\_mm}}{100}\right)^{0.6} & \text{if rain\_mm} > 0
\end{cases}$$

### Why This Form?
- **No rain (dry weather)**: Factor = 0.1 → Known hotspots still visible but suppressed
- **Light rain (20mm)**: Factor ≈ 0.5 → Moderate activation
- **Heavy rain (100mm+)**: Factor = 1.0 → Full risk (worst-case)
- **Non-linear curve**: Avoids false positives in light drizzle, responds strongly to genuine storms

### Real-Time Data
- Fetched from **Open-Meteo** (free, no API key)
- Past 24 hours of precipitation
- Sampled at city center + 4 surrounding points for spatial variation

### Result
A **dynamic risk landscape** that:
- ✅ Matches real-world behavior
- ✅ Stays off until rain appears
- ✅ Lights up hotspots first during storms
- ✅ Updates every API call

---

## 🚦 Routing Logic: Three Cost Functions

Once you have `FinalRisk(x)` for every location, you generate **three distinct routes** by optimizing different objectives:

| Route Type | Cost Function | Use Case |
|-----------|---------------|----------|
| **Fastest** | Minimize distance | Baseline, time-critical |
| **Balanced** | Minimize (distance + α × risk) | Daily default, good balance |
| **Safest** | Minimize (distance + β × risk) where β > α | Extreme weather, risk-averse users |

### Implementation Details

1. **Route generation** uses OpenRouteService (ORS):
   - Fastest: No constraints, pure distance optimization
   - Balanced: Light avoidance of flood hotspots via polygon
   - Safest: Aggressive avoidance of flood zones

2. **Risk scoring** for each route:
   - Sample route at ~100 equally-spaced points
   - For each point, fetch rainfall + compute `FinalRisk(x)`
   - Route risk score = mean of all point risks
   - Range: [0, 1] where 1 = extremely dangerous

3. **Result**: Three concrete routes with:
   - Different paths (not just reorderings)
   - Computed risk scores
   - Distance & duration in seconds
   - Coordinates for visualization

---

## 📊 Heatmap Visualization

Generates a dense grid of risk values across Mumbai:

```
Grid spacing: ~1.6 km apart (0.015° increments)
Coverage: Bounding box from 18.90°N to 19.525°N, 72.75°E to 73.225°E
Points shown: Only if FinalRisk > 0.05 (to avoid clutter)
```

Frontend renders as a color-coded overlay:
- 🔵 Blue = Low risk
- 🟡 Yellow = Medium risk
- 🔴 Red = High risk

---

## 🗂️ File Structure

```
backend/
├── main.py                    # FastAPI server, routing endpoints
├── flood_risk.py              # Core two-layer risk computation
├── models.py                  # Pydantic data models
├── config.py                  # Environment variables
├── requirements.txt           # Dependencies
└── data/
    ├── flood_pivots.csv       # Known waterlogging locations + severity
    ├── flood_prone_roads.csv  # (Optional: specific road segments)
    └── mumbai_graph.pkl       # (Optional: networkx graph for advanced routing)
```

---

## 🔌 API Endpoints

### `POST /api/routes`

**Request:**
```json
{
  "origin": {"lat": 19.0760, "lng": 72.8777},
  "destination_text": "Bandra Kurla Complex, Mumbai"
}
```

**Response:**
```json
{
  "routes": [
    {
      "id": "fastest",
      "label": "Fastest Route",
      "color": "#1E88E5",
      "distance_m": 12500,
      "duration_s": 1200,
      "risk_score": 0.35,
      "coordinates": [{"lat": 19.076, "lng": 72.878}, ...]
    },
    {
      "id": "safer",
      "label": "Balanced Route",
      "color": "#43A047",
      "distance_m": 13200,
      "duration_s": 1320,
      "risk_score": 0.22,
      "coordinates": [...]
    },
    {
      "id": "safest",
      "label": "Safest Route",
      "color": "#F4511E",
      "distance_m": 14100,
      "duration_s": 1450,
      "risk_score": 0.12,
      "coordinates": [...]
    }
  ],
  "heatmap_points": [
    {"lat": 19.076, "lng": 72.878, "intensity": 0.65},
    ...
  ]
}
```

---

## 🎯 Why This Design Is Strong

### ✅ Technically
1. **Separation of concerns**: Geography vs. weather are independent layers
2. **No overfitting**: Uses domain knowledge (real pivots), not neural nets
3. **Scalable**: Add new cities by loading different pivot CSV
4. **Caching-friendly**: Preference map is static, only rainfall updates

### ✅ Scientifically
- **Honest about limitations**: We don't predict *if* a flood will happen, we map *where* it's likely
- **Data-driven anchors**: Severity scores come from real waterlogging records
- **Physically grounded**: Exponential decay matches diffusion processes
- **Rainfall integration**: Matched to meteorological standards (24h accumulation)

### ✅ Practically
- **Works with incomplete data**: Doesn't need every street monitored
- **Improves incrementally**: Better as you log more flood incidents
- **Explainable**: Easy to justify to judges, stakeholders, users
- **No retraining**: New rainfall = immediate routing updates

---

## 🚀 Next Steps (Recommended Order)

### 1. ✅ **Precomputed Preference Map** (DONE)
   - Loaded from CSV
   - Cached in memory on startup
   - Accessible via `point_in_hotspot(lat, lng)` for visualization

### 2. ✅ **Dynamic Rainfall Integration** (DONE)
   - Fetches from Open-Meteo
   - Modulates preference map in real-time
   - Accessible via `flood_risk_at_point(lat, lng, rainfall_mm)`

### 3. ✅ **Risk-Aware Routing** (DONE)
   - Three routes: fastest, balanced, safest
   - Risk scored for each route
   - Heatmap generated

### 4. 📋 **Caching & Performance** (NEXT)
   - Cache preference map as a grid (e.g., 0.01° resolution)
   - Pre-compute heatmap and update only on rainfall change
   - Store 24h of rainfall history for trend analysis

### 5. 📋 **Validation & Tuning** (AFTER)
   - Compare route recommendations against actual flood impacts
   - Adjust SPREAD_FACTOR_KM if decay is too slow/fast
   - Add seasonal weighting (monsoon vs. dry season)

### 6. 📋 **Advanced Features** (FUTURE)
   - ML-based severity estimation from logs
   - Temporal patterns (certain hours/months riskier)
   - Social data (Twitter/community reports)
   - Historical flooding progression models

---

## 📝 One-Sentence Summary

> "We precompute a city-wide waterlogging preference map from known flood-prone locations, and dynamically activate it using real-time rainfall to produce risk-aware routing."

This is your core narrative. Defend it with confidence.

---

## 🧪 Testing the System

### Manual Test
```python
from backend.flood_risk import flood_risk_at_point, _preference_map_at_point

# Hindmata area, no rain
risk_dry = flood_risk_at_point(19.0056, 72.8417, 0.0)
print(f"Hindmata (dry): {risk_dry:.3f}")  # ~0.095 (0.95 * 0.1)

# Same location, heavy rain
risk_wet = flood_risk_at_point(19.0056, 72.8417, 100.0)
print(f"Hindmata (100mm rain): {risk_wet:.3f}")  # ~0.95 (0.95 * 1.0)

# Preference map alone (structural risk)
pref = _preference_map_at_point(19.0056, 72.8417)
print(f"Preference at Hindmata: {pref:.3f}")  # ~0.95
```

---

**Version:** 1.0  
**Last Updated:** February 2026  
**Status:** Production-Ready
