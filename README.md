# OptiRoute

[![CI Status](https://github.com/RayonBiswas/OptiRoute/actions/workflows/ci.yml/badge.svg)](https://github.com/RayonBiswas/OptiRoute/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org)
[![React + TypeScript](https://img.shields.io/badge/React-18+-61dafb.svg)](https://react.dev)

> **Intelligent route planning that avoids floods and waterlogging in Mumbai**

OptiRoute is a full-stack flood- and risk-aware route optimizer that combines real-time rainfall data (Open-Meteo), static waterlogging heuristics, and bad-road penalties to intelligently rank and explain routing choices. Built with FastAPI, React, and Leaflet.

## ✨ Features

- **Live Rainfall Integration** — Fetches Open-Meteo weather data to modulate perceived flood risk
- **Waterlogging Heuristics** — Static waterlogging pivot maps combined with live weather for dynamic scoring
- **Multi-Route Comparison** — Compare three risk-ranked routes side-by-side on an interactive map
- **Human-Readable Explanations** — Understand why each route is preferred or avoided
- **Bad-Road Penalties** — Incorporate bad-road data to penalize lower-quality roads
- **Heatmap Visualization** — Visual overlay of risk zones across the map
- **Docker Support** — Run locally or in production via Docker Compose
- **CI/CD Ready** — GitHub Actions workflow included

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Node.js 16+
- [OpenRouteService API key](https://openrouteservice.org) (free tier available)
- Git

### Backend Setup

```powershell
# Clone and navigate
git clone https://github.com/RayonBiswas/OptiRoute.git
cd OptiRoute

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Configure environment
# Create backend/.env with:
#   ORS_KEY=your_openrouteservice_api_key

# Start server
python -m uvicorn backend.main:app --reload
```

Server runs on `http://localhost:8000`

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend dev server runs on `http://localhost:5173`

## 📁 Project Structure

```
OptiRoute/
├── backend/                    # FastAPI application
│   ├── main.py                # API routes (POST /api/routes, POST /api/heatmap)
│   ├── flood_risk.py          # Risk scoring & waterlogging logic
│   ├── models.py              # Pydantic data models
│   ├── requirements.txt        # Python dependencies
│   └── data/                  # Optional static CSV data
├── frontend/                   # React + Vite + TypeScript
│   ├── src/
│   │   ├── App.tsx            # Main component & geolocation
│   │   ├── components/
│   │   │   └── MapView.tsx    # Leaflet map & route rendering
│   │   └── types.ts           # TypeScript interfaces
│   ├── package.json
│   └── vite.config.ts
├── notebooks/
│   └── waterlogging_training.ipynb  # Data exploration & scoring demo
├── docker-compose.yml         # Local stack deployment
├── Dockerfile                 # Backend image
└── README.md
```

## 🏗️ Architecture

**Backend:**
- FastAPI server with async OpenRouteService integration
- Polyline decoding for route geometry
- Rule-based scoring: **60% flood risk** + **30% bad roads** + **10% distance**
- Dynamic risk modulation via Open-Meteo rainfall

**Frontend:**
- React with React-Leaflet for interactive maps
- Geolocation-based origin detection
- Route hover/selection UI with detailed explanations
- Real-time heatmap overlay

## 📊 How It Works

1. **User enters destination** → Frontend geocodes via ORS, validates bounds (Mumbai region)
2. **Backend fetches 3 routes** → ORS Directions API returns alternatives
3. **Score each route** → Combine flood risk, bad roads, and distance
4. **Fetch weather** → Open-Meteo API for live rainfall at route segments
5. **Explain ranking** → Human-readable text justifying each route's score
6. **Visualize** → Display routes on Leaflet map with heatmap overlay

## 🔧 Configuration

Create `backend/.env`:

```env
ORS_KEY=your_openrouteservice_api_key
```

### Optional Data Files

Place CSV files in `backend/data/` (fallback synthetic data used if absent):

- `flood_pivots.csv` — Waterlogging point grid (columns: `lat`, `lon`, `risk`)
- `bad_roads.csv` — Poor-condition road points (columns: `lat`, `lon`)

## 📦 Docker

Build and run the backend in a container:

```bash
docker-compose up --build
```

API available on `http://localhost:8000`

## 🧪 Testing

Run the training notebook to explore data and scoring:

```bash
cd notebooks
jupyter notebook waterlogging_training.ipynb
```

This notebook demonstrates:
- Fetching Open-Meteo rainfall
- Synthetic waterlogging & bad-road generation
- Feature computation per route
- Weight sensitivity analysis

## 📝 API Endpoints

### `POST /api/routes`

Request:
```json
{
  "origin": [19.07, 72.88],
  "destination": "Gateway of India"
}
```

Response:
```json
{
  "routes": [
    {
      "id": 0,
      "distance": 4200,
      "duration": 420,
      "coordinates": [[19.07, 72.88], ...],
      "score": 42.5,
      "explanation": "Best route: Low flood risk (35%), minimal bad roads."
    },
    ...
  ],
  "heatmap": [[19.08, 72.89, 0.65], ...]
}
```

### `POST /api/heatmap`

Request:
```json
{
  "bounds": [[18.9, 72.7], [19.3, 73.0]]
}
```

Response:
```json
{
  "heatmap": [[19.08, 72.89, 0.65], ...]
}
```

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Commit changes: `git commit -m "Add my feature"`
4. Push: `git push origin feat/my-feature`
5. Open a Pull Request

## 📜 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## 📧 Contact

Questions or ideas? Open an [issue](https://github.com/RayonBiswas/OptiRoute/issues) or reach out to the team.

---

**Built with ❤️ for safer commutes in Mumbai.**
# 🔹 Step 1: Backend Setup & Run (FastAPI)

# Open Terminal 1:

cd C:\Rayon\Projects\optiroute

py -3.12 -m venv venv

# WAIT THIS IS HAVING ISSUE - python -m venv venv
.\venv\Scripts\Activate.ps1
dont do !!!!!! cd backend, just run from the optiroute only
pip install -r requirements.txt
python -m uvicorn main:app --reload


✅ Backend will run at:

http://127.0.0.1:8000


(Optional check)

http://127.0.0.1:8000/docs


👉 Keep this terminal running

# 🔹 Step 2: Frontend Setup & Run (React + Vite)

# Open Terminal 2:

cd C:\Rayon\Projects\optiroute\frontend
npm install
npm run dev


✅ Frontend will run at:

http://localhost:5173

🔑 Environment Variable Setup

Create file:

backend/.env


Add:

ORS_API_KEY=your_openrouteservice_api_key_here


⚠️ Restart backend after changing .env

🧠 Notes (Important)

Do NOT activate Python venv in frontend

Backend must be running before requesting routes

Use two terminals (backend + frontend)

If ports are busy, stop previous instances