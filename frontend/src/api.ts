import axios from "axios";
import { LatLng, RoutesResponse } from "./types";

export async function fetchRoutes(params: {
  origin: LatLng;
  destination_text?: string;
  destination?: LatLng;
}): Promise<RoutesResponse> {
  const resp = await axios.post<RoutesResponse>("/api/routes", params);
  return resp.data;
}