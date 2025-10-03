import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, HTTPException
from datetime import datetime

from isolate_runner import IsolateRunner, Language, RunResult, Status
from schemas.schames import BatchSubmissionRequest, BatchSubmissionResponse, SubmissionRequest, SubmissionResponse, TestResult
from runner.box_manager import BoxIDManager

logger = logging.getLogger(__name__)

box_manager = BoxIDManager()
executor = ThreadPoolExecutor(max_workers=20)

def language_to_enum(lang_str: str) -> Language:
    lang_map = {
        "python": Language.PYTHON,
        "cpp": Language.CPP,
        "c": Language.C,
        "go": Language.GO
    }
    return lang_map.get(lang_str.lower(), Language.PYTHON)

router = APIRouter()

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

@router.get("/health")
async def health_check():
    stats = box_manager.get_stats()
    
    health_status = "healthy" if stats['available_boxes'] > 10 else "degraded"
    
    return {
        "status": health_status,
        "timestamp": datetime.now().isoformat(),
        "available_boxes": stats['available_boxes'],
        "in_use_boxes": stats['in_use_boxes'],
        "total_boxes": stats['total_boxes']
    }

@router.get("/stats")
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

@router.post("/submit", response_model=SubmissionResponse)
async def submit_code(request: SubmissionRequest):
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
        loop = asyncio.get_running_loop()
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
        box_manager.release(box_id)

@router.post("/batch", response_model=BatchSubmissionResponse)
async def batch_submit(request: BatchSubmissionRequest):
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
            loop = asyncio.get_running_loop()
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
