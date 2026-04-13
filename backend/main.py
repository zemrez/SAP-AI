"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from modules.registry import discover_and_mount_modules

app = FastAPI(
    title="SAP Anomaly Detective",
    description="AI-powered financial anomaly detection for SAP ERP",
    version="1.0.0",
)

# CORS — allow the Next.js frontend and SAP BSP origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    """Liveness / readiness probe."""
    return {"status": "ok", "version": app.version}


# Auto-discover and mount feature modules
discover_and_mount_modules(app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=True,
    )
