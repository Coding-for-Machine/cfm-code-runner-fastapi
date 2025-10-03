import uvicorn
import logging
from fastapi import FastAPI
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
from routers import language, submissions

from isolate_runner import IsolateRunner
from runner.box_manager import BoxIDManager

# Logging sozlash
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=20)

# Box manager
box_manager = BoxIDManager()

# ============= Lifespan Events =============
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup va Shutdown events"""
    # Startup
    logger.info("=" * 60)
    logger.info("Isolate Code Runner API ishga tushdi")
    logger.info(f"Port: 8080")
    logger.info(f"Docs: http://0.0.0.0:8080/docs")
    logger.info(f"Box Count: {box_manager.max_boxes}")
    logger.info("=" * 60)
    
    yield
    
    # Shutdown
    logger.info("Isolate Code Runner API to'xtatilmoqda...")
    
    # Barcha box larni tozalash
    for box_id in range(box_manager.max_boxes):
        try:
            runner = IsolateRunner(box_id=box_id)
            runner.cleanup()
        except Exception:
            pass
    
    # Executor tozalash
    executor.shutdown(wait=True)
    logger.info("Executor yopildi. API to'xtatildi.")


app = FastAPI(
    title="Isolate Code Runner API",
    description="Xavfsiz kod bajarish API - Python, C++, C, Go",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS sozlamalari
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# api routers
app.include_router(language.router, prefix="/api/v1", tags=["Language"])
app.include_router(submissions.router, prefix="/api/v1", tags=["Submissions"])

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global xato handler"""
    logger.error(f"Global xato: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error 500",
            "message": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )

@app.get("/")
async def root():
    return {
        "name": "Isolate Code Runner API",
        "version": "2.0.0",
        "description": "Xavfsiz kod bajarish xizmati",
        "supported_languages": ["python", "cpp", "c", "go"],
        "endpoints": {
            "docs": "/docs",
            "health": "/api/v1/health",
            "stats": "/api/v1/stats",
            "submit": "/api/v1/submit",
            "batch": "/api/v1/batch"
        },
        "status": "running"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
        workers=1,
        log_level="info"
    )
