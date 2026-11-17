import os
import sys
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import HTTPException

# Setup directories
if getattr(sys, 'frozen', False):
    base_dir = sys._MEIPASS
    env_path = os.path.join(os.path.dirname(sys.executable), '.env')
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(base_dir, '.env')

# Load environment variables
load_dotenv(dotenv_path=env_path)

from routers import performance, alerts, settings, editor, dashboard, healthcheck
from core.database import init_db

app = FastAPI(title="Oracle Monitoring Server")

@app.on_event("startup")
async def startup_event():
    await init_db()

# Enable CORS
# allow_origins=["*"] with allow_credentials=True is rejected by browsers per the CORS spec.
# Use an explicit list from CORS_ORIGINS env var (comma-separated), falling back to localhost only.
_raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:5174,http://localhost:8000")
_allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(performance.router)
app.include_router(alerts.router)
app.include_router(settings.router)
app.include_router(editor.router)
app.include_router(dashboard.router)
app.include_router(healthcheck.router)

@app.get("/api/status")
def read_root():
    return {"status": "ok", "service": "oracle-monitoring-server"}


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "db_connection": "mock (initialized)"}

dist_dir = os.path.join(base_dir, "dist")
if os.path.exists(dist_dir):
    assets_dir = os.path.join(dist_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{file_path:path}")
    def serve_static(file_path: str):
        if file_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
            
        full_path = os.path.join(dist_dir, file_path)
        if os.path.isfile(full_path):
            return FileResponse(full_path)
            
        index_path = os.path.join(dist_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
            
        return {"error": "Frontend build not found"}

if __name__ == "__main__":
    import uvicorn
    import threading
    import webbrowser
    import time

    PORT = int(os.getenv("PORT", "8000"))
    HOST = os.getenv("HOST", "0.0.0.0")
    URL = f"http://localhost:{PORT}"

    def _open_browser():
        time.sleep(2)
        webbrowser.open(URL)

    is_development = not getattr(sys, 'frozen', False)
    if is_development:
        uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
    else:
        # exe 모드: 브라우저를 자동으로 열고 서버를 시작합니다.
        threading.Thread(target=_open_browser, daemon=True).start()
        print(f"Oracle Monitoring 서버 시작: {URL}")
        uvicorn.run(app, host=HOST, port=PORT)
