import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator
from typing import Literal, Optional
from fastapi.responses import StreamingResponse
from core.runner import box_manager, execute_code
from core.stream import stream_execution, wrap_code
from core.query import get_tests_and_execution


class CustomInput(BaseModel):
    value: str = Field(..., max_length=10000)

class RunRequest(BaseModel):
    language_name: Literal["python", "cpp", "java", "c"]
    code: str = Field(..., min_length=1, max_length=50000)
    custom_input: Optional[CustomInput] = None
    
    @validator('code')
    def validate_code(cls, v):
        dangerous = ['import os', 'import subprocess', '__import__', 'eval(', 'exec(']
        for danger in dangerous:
            if danger in v.lower():
                raise ValueError(f"Xavfli kod: {danger}")
        return v

class SubmitRequest(BaseModel):
    language_name: Literal["python", "cpp", "java", "c"]
    code: str = Field(..., min_length=1, max_length=50000)
    
    @validator('code')
    def validate_code(cls, v):
        dangerous = ['import os', 'import subprocess', '__import__', 'eval(', 'exec(']
        for danger in dangerous:
            if danger in v.lower():
                raise ValueError(f"Xavfli kod: {danger}")
        return v

# ============= API ROUTER =============
api = APIRouter(tags=["Code Execution"])

@api.post("/run/{problem_slug}")
async def run_code(problem_slug: str, request: RunRequest):
    """Custom input bilan kodni test qilish (faqat sample test cases)"""
    
    # Database'dan ma'lumot olish
    data = await get_tests_and_execution(problem_slug, request.language_name)
    if not data:
        raise HTTPException(
            status_code=404,
            detail="Problem yoki til topilmadi"
        )
    
    # Faqat sample test case'lar
    sample_tests = [tc for tc in data["test_cases"] if tc.get("is_sample", False)]
    
    if not sample_tests and not request.custom_input:
        raise HTTPException(
            status_code=404,
            detail="Sample test case'lar topilmadi"
        )
    
    async def event_generator():
        try:
            # Custom input bor bo'lsa
            if request.custom_input:
                yield f"data: {json.dumps({'type': 'start', 'total': 1}, ensure_ascii=False)}\n\n"
                
                final_code = wrap_code(request.code, data["execution_wrapper"], request.language_name)
                
                result = await execute_code(
                    language=request.language_name,
                    code=final_code,
                    test_input=request.custom_input.value,
                    expected_output=""
                )
                
                yield f"data: {json.dumps({'type': 'custom', 'result': result}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'complete'}, ensure_ascii=False)}\n\n"
            
            # Sample test case'lar
            else:
                async for event in stream_execution(
                    language=request.language_name,
                    code=request.code,
                    test_cases=sample_tests,
                    wrapper=data["execution_wrapper"]
                ):
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        
        except Exception as e:
            error_event = {"type": "error", "error": str(e)}
            yield f"data: {json.dumps(error_event)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )

@api.post("/submit/{problem_slug}")
async def submit_code(problem_slug: str, request: SubmitRequest):
    """Barcha test case'lar bilan submit qilish"""
    
    # Database'dan ma'lumot olish
    data = await get_tests_and_execution(problem_slug, request.language_name)
    if not data:
        raise HTTPException(
            status_code=404,
            detail="Problem yoki til topilmadi"
        )
    
    if not data["test_cases"]:
        raise HTTPException(
            status_code=404,
            detail="Test case'lar topilmadi"
        )
    
    async def event_generator():
        try:
            async for event in stream_execution(
                language=request.language_name,
                code=request.code,
                test_cases=data["test_cases"],
                wrapper=data["execution_wrapper"]
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        
        except Exception as e:
            error_event = {"type": "error", "error": str(e)}
            yield f"data: {json.dumps(error_event)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


@api.get("/status")
async def get_status():
    """Box status monitoring"""
    return {
        "total_boxes": 1000,
        "used_boxes": len(box_manager._used_boxes),
        "available": 1000 - len(box_manager._used_boxes)
    }