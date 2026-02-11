export interface LatLng {
    lat: number;
    lng: number;
  }
  
  export type RouteId = "fastest" | "safer" | "safest";
  
  export interface RouteSegment extends LatLng {}
  
  export interface Route {
    id: RouteId;
    label: string;
    color: string;
    distance_m: number;
    duration_s: number;
    risk_score: number;
    score?: number;
    explanation?: string;
    coordinates: RouteSegment[];
  }
  
  export interface HeatmapPoint extends LatLng {
    intensity: number;
  }
  
  export interface RoutesResponse {
    routes: Route[];
    heatmap_points: HeatmapPoint[];
  }