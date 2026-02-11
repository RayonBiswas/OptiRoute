# Backend

Run the backend API (FastAPI) and configure the ORS key.

Environment

- Create `backend/.env` with `ORS_KEY=your_openrouteservice_key`.

Run locally

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Notes

- The backend uses `backend/data` for optional static datasets. If absent, synthetic fallbacks are used.
- Logs print geocoding and routing diagnostics to help debugging.
