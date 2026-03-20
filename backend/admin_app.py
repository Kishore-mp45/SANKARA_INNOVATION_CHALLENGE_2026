"""
PatientPath AI - Admin Portal
==============================
Separate FastAPI application for admin access on port 5000.
Serves admin_login.html as the landing page.

Run standalone:
    python admin_app.py

Or it auto-starts when you run main.py (python main.py)
"""

import sys
import os
import uvicorn
import threading
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from config import settings
from database.database import init_db
from routers.auth import router as auth_router

# Resolve frontend directory
frontend_dir = os.path.join(os.path.dirname(backend_dir), "frontend")

admin_app = FastAPI(
    title="PatientPath AI - Admin Portal",
    description="Admin-only access portal",
    version=settings.APP_VERSION,
    docs_url="/admin-docs",
)

# CORS
admin_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount auth router so /auth/admin-login works on port 5000
admin_app.include_router(auth_router)


@admin_app.get("/", response_class=HTMLResponse)
async def admin_root():
    """Serve admin_login.html as the root page."""
    login_path = os.path.join(frontend_dir, "admin_login.html")
    if os.path.isfile(login_path):
        with open(login_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Admin Login page not found</h1>", status_code=404)


# Serve frontend static files (css, js, assets) for the admin login page
if os.path.isdir(frontend_dir):
    admin_app.mount("/css", StaticFiles(directory=os.path.join(frontend_dir, "css")), name="admin-css")
    admin_app.mount("/js", StaticFiles(directory=os.path.join(frontend_dir, "js")), name="admin-js")
    assets_dir = os.path.join(frontend_dir, "assets")
    if os.path.isdir(assets_dir):
        admin_app.mount("/assets", StaticFiles(directory=assets_dir), name="admin-assets")


def start_admin_server():
    """Start the admin portal server in a background thread."""
    def _run():
        uvicorn.run(
            admin_app,
            host=settings.HOST,
            port=settings.ADMIN_PORT,
            log_level="info",
        )

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return thread


if __name__ == "__main__":
    init_db()
    print(f"\n  Admin Portal running at: http://localhost:{settings.ADMIN_PORT}\n")
    uvicorn.run(
        "admin_app:admin_app",
        host=settings.HOST,
        port=settings.ADMIN_PORT,
        reload=False,
        log_level="info",
    )
