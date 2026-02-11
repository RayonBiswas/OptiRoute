
# OptiRoute

[![CI](https://github.com/RayonBiswas/OptiRoute/actions/workflows/ci.yml/badge.svg)](https://github.com/RayonBiswas/OptiRoute/actions)

OptiRoute is a flood- and risk-aware route planner focused on Mumbai, India. It combines OpenRouteService routing with live rainfall (Open-Meteo) and static waterlogging/bad-road heuristics to rank and explain route choices.

Quick start

Backend (Python):

```powershell
python -m venv venv
venv\Scripts\activate
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload
```

Frontend (Node):

```bash
cd frontend
npm install
npm run dev
```

Project structure

- `backend/` — FastAPI backend, routing, flood-risk logic
- `frontend/` — React + TypeScript frontend (Vite)
- `notebooks/` — training & data exploration

Recommended workflow

1. Configure `backend/.env` with your OpenRouteService API key as `ORS_KEY`.
2. Start the backend and frontend as shown above.
3. Use the UI to test routes and view risk-aware scores.

Contributing

Please read `CONTRIBUTING.md` and follow the code style and PR process.

License

This project is released under the MIT license. See `LICENSE`.
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