import os
from dotenv import load_dotenv
import openrouteservice

# Load .env file
load_dotenv()

api_key = os.getenv("ORS_API_KEY")
print("API key loaded:", bool(api_key))

client = openrouteservice.Client(key=api_key)

route = client.directions(
    coordinates=[
        (77.5946, 12.9716),  # lon, lat
        (77.6200, 12.9352)
    ],
    profile="foot-walking",
    format="geojson"
)

summary = route["features"][0]["properties"]["summary"]

print("Distance (m):", summary["distance"])
print("Duration (s):", summary["duration"])
