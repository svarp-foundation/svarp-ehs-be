# SVARP EHS Platform - Backend

FastAPI backend for the SVARP EHS Platform, utilizing a multi-tenant architecture with SQLite.

## Features

- **Multi-tenancy**:
  - `master.db` handles authentication and company mapping.
  - Per-company SQLite databases (`company_{id}.db`) for data isolation.
- **Authentication**: JWT-based auth with Role-Based Access Control (Admin, Auditor, etc.).
- **Modules**:
  - **Site Management**: Sites and Departments.
  - **Audit Management**: Full lifecycle (Planned -> In Progress -> Completed -> Locked).
  - **Findings Management**: Risk assessment, Assignment, Status tracking.
  - **Dashboard**: Role-aware analytics and KPIs.

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   ```
2. **Configuration**:
   - Create a `.env` file in the `backend` directory.
   - Add `DATABASE_DIR=tmp/ehs_db`.

3. **Run Server**:
   ```bash
   uvicorn app.main:app --reload
   ```
   Server runs at `http://localhost:8000`.

3. **Database**:
   - Databases are automatically created in `tmp/ehs_db/` upon access.
   - Master DB is initialized on first run.

## API Documentation

- Swagger UI available at `http://localhost:8000/docs`.
- Redoc available at `http://localhost:8000/redoc`.

## Testing

Run verification scripts in `tests/`:
```bash
python3 tests/verify_site_management.py
python3 tests/verify_audit_lifecycle.py
python3 tests/verify_finding_management.py
python3 tests/verify_dashboard.py
```
