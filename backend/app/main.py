import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import BASE_DIR, Base, SessionLocal, engine
from .migrations import run_lightweight_migrations
from .routers import (
    agents,
    case_files,
    cases,
    companies,
    deadline_rules,
    deadlines,
    documents,
    settings,
)
from .seed_data import seed_deadline_rules
from .services.company_utils import (
    backfill_case_agents,
    backfill_case_companies,
    backfill_case_patent_types,
)
from .services.twin import backfill_twins

app = FastAPI(title="专利管理系统")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents.router)
app.include_router(companies.router)
app.include_router(cases.router)
app.include_router(case_files.router)
app.include_router(documents.router)
app.include_router(deadlines.router)
app.include_router(deadline_rules.router)
app.include_router(settings.router)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    run_lightweight_migrations(engine, Base.metadata)
    db = SessionLocal()
    try:
        seed_deadline_rules(db)
        backfill_case_companies(db)
        backfill_case_patent_types(db)
        backfill_twins(db)
        backfill_case_agents(db)
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}


# In the packaged exe, PyInstaller bundles the built frontend under
# frontend_dist/ alongside the app; in dev (running `uvicorn app.main:app`
# directly, without `npm run dev`) it falls back to the built dist next to
# the frontend project, if present. When neither exists (normal dev flow
# where the frontend runs via its own Vite dev server on :5173), no static
# routes are registered and the API-only server behaves as before.
if getattr(sys, "frozen", False):
    FRONTEND_DIST = Path(sys._MEIPASS) / "frontend_dist"  # type: ignore[attr-defined]
else:
    FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
