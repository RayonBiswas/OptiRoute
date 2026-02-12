import React, { useEffect, useRef } from "react";
import { MapContainer, TileLayer, Polyline, Marker, Popup, useMap, Circle } from "react-leaflet";
import L, { LatLngExpression } from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.heat";
import { HeatmapPoint, Route } from "../types";

// Fix for default markers in react-leaflet
import icon from "leaflet/dist/images/marker-icon.png";
import iconShadow from "leaflet/dist/images/marker-shadow.png";

let DefaultIcon = L.icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

L.Marker.prototype.options.icon = DefaultIcon;

interface Props {
  routes: Route[];
  showHeatmap: boolean;
  heatmapPoints: HeatmapPoint[];
  origin?: { lat: number; lng: number };
  destination?: { lat: number; lng: number };
  selectedRouteId?: string | null;
  hoveredRouteId?: string | null;
}

const DEFAULT_CENTER: LatLngExpression = [19.076, 72.8777]; // Mumbai

function FitBoundsOnRoutes({
  routes,
  origin,
  destination
}: {
  routes: Route[];
  origin?: { lat: number; lng: number };
  destination?: { lat: number; lng: number };
}) {
  const map = useMap();

  useEffect(() => {
    const latlngs: LatLngExpression[] = [];

    // Collect all route points
    routes.forEach(route => {
      route.coordinates.forEach(c => {
        if (c.lat && c.lng) {
          latlngs.push([c.lat, c.lng]);
        }
      });
    });

    // Add markers if available
    if (origin && origin.lat && origin.lng) {
      latlngs.push([origin.lat, origin.lng]);
    }
    if (destination && destination.lat && destination.lng) {
      latlngs.push([destination.lat, destination.lng]);
    }

    // Only fit bounds if we have valid points
    if (latlngs.length > 0) {
      try {
        const bounds = L.latLngBounds(latlngs as any);
        map.fitBounds(bounds, { 
          padding: [80, 80],
          maxZoom: 14
        });
      } catch (e) {
        console.error("Error fitting bounds:", e);
        map.setView(DEFAULT_CENTER, 12);
      }
    } else {
      // Default to Mumbai center
      map.setView(DEFAULT_CENTER, 12);
    }
  }, [routes, origin, destination, map]);

  return null;
}

function HeatmapLayer({
  points,
  show
}: {
  points: HeatmapPoint[];
  show: boolean;
}) {
  const map = useMap();
  const layerRef = useRef<any>(null);

  useEffect(() => {
    // Remove existing heatmap if hiding
    if (!show) {
      if (layerRef.current) {
        map.removeLayer(layerRef.current);
        layerRef.current = null;
      }
      return;
    }

    // Remove old heatmap before creating new one
    if (layerRef.current) {
      map.removeLayer(layerRef.current);
    }

    // Create heatmap with data
    const heatData = points.map(p => [p.lat, p.lng, p.intensity] as [number, number, number]);

    if (heatData.length > 0) {
      layerRef.current = (L as any).heatLayer(heatData, {
        radius: 30,
        blur: 20,
        maxZoom: 17,
        minOpacity: 0.2,
        gradient: {
          0.0: "#0000ff",   // Blue - low risk
          0.5: "#ffff00",   // Yellow - medium risk
          1.0: "#ff0000"    // Red - high risk
        }
      });
      layerRef.current.addTo(map);
    }

    return () => {
      if (layerRef.current) {
        map.removeLayer(layerRef.current);
        layerRef.current = null;
      }
    };
  }, [points, show, map]);

  return null;
}

// Helper function to get color based on intensity
function getColorForIntensity(intensity: number): string {
  if (intensity < 0.2) return "#0000ff";   // Blue - low risk
  if (intensity < 0.4) return "#00ff00";   // Green - low-medium
  if (intensity < 0.6) return "#ffff00";   // Yellow - medium
  if (intensity < 0.8) return "#ff8800";   // Orange - high
  return "#ff0000";                         // Red - very high
}

// Component to render risk circles as visible symbols
function RiskCirclesLayer({
  points,
  show
}: {
  points: HeatmapPoint[];
  show: boolean;
}) {
  if (!show || points.length === 0) return null;

  return (
    <>
      {points.map((point, idx) => {
        const color = getColorForIntensity(point.intensity);
        const radius = 200 + point.intensity * 1000; // Scale radius with intensity (200-1200m)
        const fillOpacity = 0.3 + point.intensity * 0.4; // More intense = more opaque
        
        return (
          <Circle
            key={`risk-${idx}`}
            center={[point.lat, point.lng]}
            radius={radius}
            color={color}
            fillColor={color}
            weight={2}
            opacity={0.6}
            fillOpacity={fillOpacity}
          >
            <Popup>
              <div style={{ fontSize: "12px" }}>
                <strong>🚨 Flood Risk</strong><br />
                Lat: {point.lat.toFixed(5)}<br />
                Lng: {point.lng.toFixed(5)}<br />
                Intensity: {(point.intensity * 100).toFixed(0)}%<br />
                <span style={{ color: color, fontWeight: "bold" }}>
                  {point.intensity > 0.7 ? "HIGH RISK" : point.intensity > 0.5 ? "MEDIUM RISK" : "LOW RISK"}
                </span>
              </div>
            </Popup>
          </Circle>
        );
      })}
    </>
  );
}

const MapView: React.FC<Props> = ({
  routes,
  showHeatmap,
  heatmapPoints,
  origin,
  destination,
  selectedRouteId,
  hoveredRouteId,
}) => {
  return (
    <MapContainer
      className="map-container"
      center={DEFAULT_CENTER}
      zoom={11}
      style={{ width: "100%", height: "100%" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      <FitBoundsOnRoutes
        routes={routes}
        origin={origin}
        destination={destination}
      />

      {origin && (
        <Marker position={[origin.lat, origin.lng]}>
          <Popup>
            <div style={{ fontSize: "12px" }}>
              <strong>📍 Start Location</strong><br />
              Lat: {origin.lat.toFixed(5)}<br />
              Lng: {origin.lng.toFixed(5)}
            </div>
          </Popup>
        </Marker>
      )}

      {destination && (
        <Marker position={[destination.lat, destination.lng]}>
          <Popup>
            <div style={{ fontSize: "12px" }}>
              <strong>🎯 Destination</strong><br />
              Lat: {destination.lat.toFixed(5)}<br />
              Lng: {destination.lng.toFixed(5)}
            </div>
          </Popup>
        </Marker>
      )}

      {routes.map(route => {
        // If a route is selected, show only that route
        if (selectedRouteId && route.id !== selectedRouteId) return null;

        const isHovered = !selectedRouteId && hoveredRouteId === route.id;
        const isSelected = Boolean(selectedRouteId && route.id === selectedRouteId);

        return (
          <Polyline
            key={route.id}
            positions={route.coordinates.map(c => [c.lat, c.lng] as LatLngExpression)}
            color={route.color}
            weight={isSelected ? 8 : isHovered ? 6 : 4}
            opacity={isSelected ? 1 : isHovered ? 0.95 : 0.45}
            dashArray={route.id === "fastest" ? undefined : "5, 5"}
            lineCap="round"
            lineJoin="round"
          >
            <Popup>
              <div style={{ fontSize: "12px" }}>
                <strong>{route.label}</strong><br />
                Distance: {(route.distance_m / 1000).toFixed(1)} km<br />
                Duration: {Math.round(route.duration_s / 60)} min<br />
                Risk Score: {route.score?.toFixed(2) ?? "N/A"}
                {route.explanation ? (
                  <div style={{ marginTop: 6, color: "#333" }}>{route.explanation}</div>
                ) : null}
              </div>
            </Popup>
          </Polyline>
        );
      })}

      <HeatmapLayer points={heatmapPoints} show={showHeatmap} />
      <RiskCirclesLayer points={heatmapPoints} show={showHeatmap} />
    </MapContainer>
  );
};

export default MapView;