import axios from "axios";
import { LatLng, RoutesResponse, HeatmapPoint } from "./types";

export async function fetchRoutes(params: {
  origin: LatLng;
  destination_text?: string;
  destination?: LatLng;
}): Promise<RoutesResponse> {
  const resp = await axios.post<RoutesResponse>("/api/routes", params);
  return resp.data;
}

export async function fetchHeatmap(): Promise<HeatmapPoint[]> {
  const resp = await axios.get<{ heatmap_points: HeatmapPoint[] }>("/api/heatmap");
  return resp.data.heatmap_points;
}