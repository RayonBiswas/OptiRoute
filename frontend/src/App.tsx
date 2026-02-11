import React, { useEffect, useState } from "react";
import MapView from "./components/MapView";
import { LatLng, Route, HeatmapPoint, RoutesResponse } from "./types";
import { fetchRoutes } from "./api";

const DEFAULT_ORIGIN: LatLng = { lat: 19.076, lng: 72.8777 };

const App: React.FC = () => {
  const [origin, setOrigin] = useState<LatLng | undefined>(undefined);
  const [destinationText, setDestinationText] = useState("");
  const [routes, setRoutes] = useState<Route[]>([]);
  const [heatmapPoints, setHeatmapPoints] = useState<HeatmapPoint[]>([]);
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<string>("Initializing location...");
  const [destinationCoord, setDestinationCoord] = useState<LatLng | undefined>(
    undefined
  );
  const [locationReady, setLocationReady] = useState(false);
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null);
  const [hoveredRouteId, setHoveredRouteId] = useState<string | null>(null);

  // Get current location once at startup (fallback to Mumbai center if blocked)
  useEffect(() => {
    if (!navigator.geolocation) {
      setOrigin(DEFAULT_ORIGIN);
      setLocationReady(true);
      setStatus("Geolocation not available; using Mumbai center");
      return;
    }

    const timer = setTimeout(() => {
      // Timeout fallback: if geolocation takes too long, use default
      if (!locationReady) {
        setOrigin(DEFAULT_ORIGIN);
        setLocationReady(true);
        setStatus("Location timeout; using Mumbai center");
      }
    }, 5000);

    navigator.geolocation.getCurrentPosition(
      pos => {
        clearTimeout(timer);
        const loc = {
          lat: pos.coords.latitude,
          lng: pos.coords.longitude
        };
        setOrigin(loc);
        setLocationReady(true);
        setStatus("Using your current location");
      },
      () => {
        clearTimeout(timer);
        setOrigin(DEFAULT_ORIGIN);
        setLocationReady(true);
        setStatus("Location blocked; using Mumbai center");
      },
      { enableHighAccuracy: true, timeout: 8000 }
    );
  }, []);

  const handleSearch = async () => {
    if (!locationReady) {
      setStatus("Still initializing location...");
      return;
    }
    if (!origin) {
      setStatus("Origin not available");
      return;
    }
    if (!destinationText.trim()) {
      setStatus("Enter a destination in Mumbai");
      return;
    }

    setLoading(true);
    setStatus("Fetching routes...");
    try {
      const body = {
        origin,
        destination_text: destinationText.trim()
      };
      const data: RoutesResponse = await fetchRoutes(body);
      setRoutes(data.routes);
      setHeatmapPoints(data.heatmap_points);

      // Approximate destination as last point of fastest route for map fitting
      const fastest = data.routes.find(r => r.id === "fastest");
      if (fastest && fastest.coordinates.length > 0) {
        const last = fastest.coordinates[fastest.coordinates.length - 1];
        setDestinationCoord({ lat: last.lat, lng: last.lng });
      }

      setStatus(
        `Loaded ${data.routes.length} routes · fastest ${(data.routes[0].duration_s / 60).toFixed(
          1
        )} min`
      );
    } catch (err: any) {
      console.error(err);
      setStatus(`Error: ${err.response?.data?.detail || "Failed to fetch routes"}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-shell">
      <div className="top-bar">
        <div className="top-bar-title">OptiRoute · Mumbai</div>

        <div className="top-bar-input">
          <input
            type="text"
            placeholder="Destination in Mumbai (e.g. Bandra Kurla Complex)"
            value={destinationText}
            onChange={e => setDestinationText(e.target.value)}
            onKeyDown={e => {
              if (e.key === "Enter") handleSearch();
            }}
          />
          <button disabled={loading || !locationReady} onClick={handleSearch}>
            {loading ? "Routing..." : locationReady ? "Find routes" : "Initializing..."}
          </button>
        </div>

        <div className="top-bar-right">
          <label className="toggle">
            <input
              type="checkbox"
              checked={showHeatmap}
              onChange={e => setShowHeatmap(e.target.checked)}
            />
            <span>Flood heatmap</span>
          </label>
          <span className="status-text">
            {status}
          </span>
        </div>
      </div>

      <div className="routes-panel" style={{ padding: 8, borderBottom: "1px solid #eee" }}>
        {routes.length > 0 ? (
          <div className="route-options">
            {routes.map(r => (
              <label
                key={r.id}
                style={{ display: "block", margin: "6px 0", cursor: "pointer" }}
                onMouseEnter={() => setHoveredRouteId(r.id)}
                onMouseLeave={() => setHoveredRouteId(null)}
              >
                <input
                  type="radio"
                  name="selectedRoute"
                  checked={selectedRouteId === r.id}
                  onChange={() => setSelectedRouteId(r.id)}
                />
                <strong style={{ marginLeft: 8 }}>{r.label}</strong>
                <span style={{ marginLeft: 12, color: "#555" }}>
                  {(r.duration_s / 60).toFixed(0)} min · Risk: {r.risk_score.toFixed(2)}
                </span>
              </label>
            ))}
          </div>
        ) : (
          <div style={{ padding: 8, color: "#666" }}>No routes yet</div>
        )}
      </div>

      <MapView
        routes={routes}
        showHeatmap={showHeatmap}
        heatmapPoints={heatmapPoints}
        origin={origin}
        destination={destinationCoord}
        selectedRouteId={selectedRouteId}
        hoveredRouteId={hoveredRouteId}
      />
    </div>
  );
};

export default App;