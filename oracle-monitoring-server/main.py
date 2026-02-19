from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import performance, alerts, settings, editor

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(performance.router)
app.include_router(alerts.router)
app.include_router(settings.router)
app.include_router(editor.router)
app.include_router(settings.router)

@app.get("/")
def read_root():
    return {"status": "ok", "service": "oracle-monitoring-server"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "db_connection": "mock (initialized)"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
