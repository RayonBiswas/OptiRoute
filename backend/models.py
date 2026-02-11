from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class LatLng(BaseModel):
    lat: float
    lng: float


class RouteRequest(BaseModel):
    origin: LatLng
    destination_text: Optional[str] = Field(
        default=None,
        description="Human readable address, e.g. 'Bandra Kurla Complex, Mumbai'",
    )
    destination: Optional[LatLng] = Field(
        default=None,
        description="Optional explicit coordinates for destination. If provided, takes precedence over destination_text.",
    )


class RouteSegment(BaseModel):
    lat: float
    lng: float


class RouteResponseItem(BaseModel):
    id: Literal["fastest", "safer", "safest"]
    label: str
    color: str
    distance_m: float
    duration_s: float
    risk_score: float
    score: float = 0.0
    explanation: str = ""
    coordinates: List[RouteSegment]


class HeatmapPoint(BaseModel):
    lat: float
    lng: float
    intensity: float


class RoutesResponse(BaseModel):
    routes: List[RouteResponseItem]
    heatmap_points: List[HeatmapPoint]