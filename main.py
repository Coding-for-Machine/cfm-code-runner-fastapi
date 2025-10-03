"""
main.py - Isolate Code Runner API Server
FastAPI asosida yaratilgan REST API
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
import uvicorn
from enum import Enum
import asyncio
from concurrent.futures import ThreadPoolExecutor
import sys
import os
from datetime import datetime
import logging

# Isolate runner ni import qilish
from isolate_runner import IsolateRunner, Language, Status, RunResult

# Logging sozlash
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
        except:
            pass
    
    executor.shutdown(wait=True)
    logger.info("To'xtatildi.")


# FastAPI app yaratish
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

# ThreadPool executor
executor = ThreadPoolExecutor(max_workers=20)


# ============= Box ID Manager =============
class BoxIDManager:
    """Box ID larni boshqarish"""
    
    def __init__(self, max_boxes: int = 100):
        self.max_boxes = max_boxes
        self.available = set(range(max_boxes))
        self.in_use = set()
        self.stats = {
            'total_requests': 0,
            'successful_runs': 0,
            'failed_runs': 0
        }
    
    def acquire(self) -> Optional[int]:
        """Box ID olish"""
        if not self.available:
            return None
        box_id = self.available.pop()
        self.in_use.add(box_id)
        return box_id
    
    def release(self, box_id: int):
        """Box ID ni qaytarish"""
        if box_id in self.in_use:
            self.in_use.remove(box_id)
            self.available.add(box_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Statistikani olish"""
        return {
            **self.stats,
            'available_boxes': len(self.available),
            'in_use_boxes': len(self.in_use),
            'total_boxes': self.max_boxes
        }


box_manager = BoxIDManager()


# ============= Pydantic Models =============
class LanguageEnum(str, Enum):
    """Qo'llab-quvvatlanadigan dasturlash tillari"""
    python = "python"
    cpp = "cpp"
    c = "c"
    go = "go"


class SubmissionRequest(BaseModel):
    """Kod yuborish so'rovi"""
    source_code: str = Field(..., description="Manba kod", min_length=1)
    language: LanguageEnum = Field(..., description="Dasturlash tili")
    input_data: str = Field(default="", description="Kirish ma'lumotlari")
    time_limit: float = Field(
        default=1.0, 
        gt=0, 
        le=10, 
        description="Vaqt limiti (soniyada)"
    )
    memory_limit: int = Field(
        default=262144, 
        gt=0, 
        le=1048576, 
        description="Xotira limiti (KB)"
    )

    @field_validator('source_code')
    @classmethod
    def validate_source_code(cls, v):
        if len(v.strip()) == 0:
            raise ValueError("Manba kod bo'sh bo'lishi mumkin emas")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "source_code": "n = int(input())\nprint(n ** 2)",
                "language": "python",
                "input_data": "5",
                "time_limit": 1.0,
                "memory_limit": 262144
            }
        }


class SubmissionResponse(BaseModel):
    """Kod bajarilish natijasi"""
    status: str
    time: float
    memory: int
    exit_code: int
    stdout: str
    stderr: str
    message: str
    timestamp: str


class TestCase(BaseModel):
    """Bitta test case"""
    input: str = Field(default="", description="Kirish ma'lumotlari")
    expected_output: Optional[str] = Field(None, description="Kutilayotgan chiqish")


class BatchSubmissionRequest(BaseModel):
    """Bir nechta test case bilan kod yuborish"""
    source_code: str = Field(..., min_length=1)
    language: LanguageEnum
    test_cases: List[TestCase] = Field(..., min_items=1, max_items=50)
    time_limit: float = Field(default=1.0, gt=0, le=10)
    memory_limit: int = Field(default=262144, gt=0, le=1048576)

    class Config:
        json_schema_extra = {
            "example": {
                "source_code": "n = int(input())\nprint(n * 2)",
                "language": "python",
                "test_cases": [
                    {"input": "5", "expected_output": "10"},
                    {"input": "10", "expected_output": "20"}
                ],
                "time_limit": 1.0,
                "memory_limit": 262144
            }
        }


class TestResult(BaseModel):
    """Test case natijasi"""
    test_number: int
    status: str
    time: float
    memory: int
    stdout: str
    stderr: str
    input_data: str
    expected_output: Optional[str] = None
    passed: Optional[bool] = None
    message: str = ""


class BatchSubmissionResponse(BaseModel):
    """Batch submission natijasi"""
    total_tests: int
    passed_tests: int
    failed_tests: int
    total_time: float
    average_time: float
    results: List[TestResult]


# ============= Helper Functions =============
def language_to_enum(lang_str: str) -> Language:
    """String tilni Language enum ga o'zgartirish"""
    lang_map = {
        "python": Language.PYTHON,
        "cpp": Language.CPP,
        "c": Language.C,
        "go": Language.GO
    }
    return lang_map.get(lang_str.lower(), Language.PYTHON)


def run_code_sync(box_id: int, source_code: str, language: Language,
                  input_data: str, time_limit: float, memory_limit: int) -> RunResult:
    """Kodni sinxron bajarish"""
    try:
        runner = IsolateRunner(box_id=box_id)
        result = runner.run(source_code, language, input_data, time_limit, memory_limit)
        
        # Statistikani yangilash
        if result.status == Status.OK:
            box_manager.stats['successful_runs'] += 1
        else:
            box_manager.stats['failed_runs'] += 1
        
        return result
    except Exception as e:
        logger.error(f"Box {box_id} da xato: {str(e)}")
        box_manager.stats['failed_runs'] += 1
        return RunResult(
            status=Status.IE,
            message=f"Ichki xato: {str(e)}"
        )


# ============= API Endpoints =============
@app.get("/")
async def root():
    """API asosiy ma'lumotlari"""
    return {
        "name": "Isolate Code Runner API",
        "version": "2.0.0",
        "description": "Xavfsiz kod bajarish xizmati",
        "supported_languages": ["python", "cpp", "c", "go"],
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "stats": "/stats",
            "submit": "/api/submit",
            "batch": "/api/batch"
        },
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Sog'liqni tekshirish"""
    stats = box_manager.get_stats()
    
    health_status = "healthy" if stats['available_boxes'] > 10 else "degraded"
    
    return {
        "status": health_status,
        "timestamp": datetime.now().isoformat(),
        "available_boxes": stats['available_boxes'],
        "in_use_boxes": stats['in_use_boxes'],
        "total_boxes": stats['total_boxes']
    }


@app.get("/stats")
async def get_stats():
    """Detallangan statistika"""
    stats = box_manager.get_stats()
    
    success_rate = 0
    if stats['total_requests'] > 0:
        success_rate = (stats['successful_runs'] / stats['total_requests']) * 100
    
    return {
        **stats,
        "success_rate": f"{success_rate:.2f}%",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/submit", response_model=SubmissionResponse)
async def submit_code(request: SubmissionRequest):
    """
    Bitta kodni bajarish
    
    - **source_code**: Manba kod
    - **language**: python, cpp, c, go
    - **input_data**: Kirish ma'lumotlari (ixtiyoriy)
    - **time_limit**: Maksimal vaqt (soniyada)
    - **memory_limit**: Maksimal xotira (KB)
    """
    box_manager.stats['total_requests'] += 1
    
    # Box ID olish
    box_id = box_manager.acquire()
    if box_id is None:
        raise HTTPException(
            status_code=503,
            detail="Barcha sandbox lar band. Iltimos, keyinroq urinib ko'ring."
        )
    
    logger.info(f"Request qabul qilindi - Box ID: {box_id}, Language: {request.language}")
    
    try:
        # Language enum ga o'tkazish
        language = language_to_enum(request.language.value)
        
        # Asinxron bajarish
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            run_code_sync,
            box_id,
            request.source_code,
            language,
            request.input_data,
            request.time_limit,
            request.memory_limit
        )
        
        logger.info(f"Box {box_id} tugadi - Status: {result.status.value}, Time: {result.time}s")
        
        return SubmissionResponse(
            status=result.status.value,
            time=result.time,
            memory=result.memory,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            message=result.message,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Box {box_id} da xato: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ichki xato: {str(e)}")
    
    finally:
        # Box ID ni qaytarish
        box_manager.release(box_id)


@app.post("/api/batch", response_model=BatchSubmissionResponse)
async def batch_submit(request: BatchSubmissionRequest):
    """
    Bir nechta test case larni bajarish
    
    - Har bir test case uchun dastur alohida bajariladi
    - Natijalar taqqoslanadi va ball hisoblanadi
    """
    box_manager.stats['total_requests'] += len(request.test_cases)
    
    logger.info(f"Batch request - Tests: {len(request.test_cases)}, Language: {request.language}")
    
    language = language_to_enum(request.language.value)
    results = []
    passed_count = 0
    total_time = 0.0
    
    # Har bir test case ni bajarish
    for i, test_case in enumerate(request.test_cases):
        # Box ID olish (kutish bilan)
        box_id = box_manager.acquire()
        while box_id is None:
            await asyncio.sleep(0.1)
            box_id = box_manager.acquire()
        
        try:
            input_data = test_case.input
            expected_output = test_case.expected_output
            
            # Kodni bajarish
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                executor,
                run_code_sync,
                box_id,
                request.source_code,
                language,
                input_data,
                request.time_limit,
                request.memory_limit
            )
            
            total_time += result.time
            
            # Natijani tekshirish
            passed = None
            if expected_output is not None and result.status == Status.OK:
                passed = result.stdout.strip() == expected_output.strip()
                if passed:
                    passed_count += 1
            
            results.append(TestResult(
                test_number=i + 1,
                status=result.status.value,
                time=result.time,
                memory=result.memory,
                stdout=result.stdout,
                stderr=result.stderr,
                input_data=input_data,
                expected_output=expected_output,
                passed=passed,
                message=result.message
            ))
            
        except Exception as e:
            logger.error(f"Test {i+1} da xato: {str(e)}")
            results.append(TestResult(
                test_number=i + 1,
                status="IE",
                time=0.0,
                memory=0,
                stdout="",
                stderr="",
                input_data=test_case.input,
                expected_output=test_case.expected_output,
                passed=False,
                message=f"Ichki xato: {str(e)}"
            ))
        
        finally:
            box_manager.release(box_id)
    
    average_time = total_time / len(request.test_cases) if request.test_cases else 0.0
    
    logger.info(f"Batch tugadi - Passed: {passed_count}/{len(request.test_cases)}")
    
    return BatchSubmissionResponse(
        total_tests=len(request.test_cases),
        passed_tests=passed_count,
        failed_tests=len(request.test_cases) - passed_count,
        total_time=total_time,
        average_time=average_time,
        results=results
    )


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global xato handler"""
    logger.error(f"Global xato: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )


if __name__ == "__main__":
    # Serverni ishga tushirish
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
        workers=1,
        log_level="info"
    )