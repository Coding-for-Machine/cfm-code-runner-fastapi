import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator
from typing import List, Literal, Optional
from fastapi.responses import StreamingResponse
from core.runner import box_manager, execute_code
from core.stream import stream_execution, wrap_code
from core.query import get_tests_and_execution


class CustomInput(BaseModel):
    value: str = Field(..., max_length=1000)

class TestCase(BaseModel):
    input_txt: str
    output_txt: str

class RunRequest(BaseModel):
    language_name: Literal["python", "javascript", "typescript", "go", "cpp", "c", "java"]
    code: str = Field(..., min_length=1, max_length=50000)
    custom_input: Optional[CustomInput] = None
    test_cases: Optional[List[TestCase]] = None
    
    

# ============= API ROUTER =============
api = APIRouter(tags=["Code Execution"])

@api.post("/run/{problem_slug}")
async def run_code(problem_slug: str, request: RunRequest):
    """
    Code execution endpoint:
    - Run mode: custom_input mavjud
    - Submit mode: custom_input yo'q
    """
    
    async def event_generator():
        try:
            data = await get_tests_and_execution(problem_slug, request.language_name)
            
            # ====== RUN MODE (custom input bilan) ======
            if request.custom_input and request.test_cases is None:
                # Agar wrapper bo'lmasa, oddiy execute
                if not data or not data.get("execution_wrapper"):
                    yield f"data: {json.dumps({'type': 'start', 'total': 1}, ensure_ascii=False)}\n\n"
                    
                    result = await execute_code(
                        language=request.language_name,
                        code=request.code,
                        test_input=request.custom_input.value,
                        expected_output=""
                    )
                    
                    # Agar stdin dan o'qish kerak bo'lsa
                    if result.get("needs_input"):
                        yield f"data: {json.dumps({'type': 'needs_input', 'message': 'Please provide input'}, ensure_ascii=False)}\n\n"
                        return
                    
                    yield f"data: {json.dumps({'type': 'custom', 'result': result}, ensure_ascii=False)}\n\n"
                    yield f"data: {json.dumps({'type': 'complete'}, ensure_ascii=False)}\n\n"
                
                # Wrapper bilan execute
                else:
                    final_code = wrap_code(request.code, data["execution_wrapper"])
                    
                    # Bitta test case sifatida run qilish
                    input_test_case = {
                        "input_txt": request.custom_input.value,
                        "output_txt": "",
                        "is_sample": False
                    }
                    async for event in stream_execution(
                        language=request.language_name,
                        code=final_code,
                        test_cases=[input_test_case],
                        is_custom_run=True
                    ):
                        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                    if request.test_cases:
                        async for event in stream_execution(
                            language=request.language_name,
                            code=final_code,
                            test_cases=request.test_cases,
                            wrapper=data["execution_wrapper"],
                            is_custom_run=True
                        ):
                            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            
            # ====== SUBMIT MODE (custom input yo'q) ======
            else:
                if not data or not data.get("test_cases"):
                    raise HTTPException(status_code=400, detail="Test cases not found for this problem")
                
                all_test_cases = data["test_cases"]
                if request.test_cases:
                    all_test_cases.extend([tc.dict() for tc in request.test_cases])
                
                final_code = wrap_code(request.code, data["execution_wrapper"], request.language_name)
                
                async for event in stream_execution(
                    language=request.language_name,
                    code=final_code,
                    test_cases=all_test_cases,
                    wrapper=data["execution_wrapper"],
                    is_custom_run=False
                ):
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        
        except HTTPException as he:
            error_event = {"type": "error", "error": he.detail}
            yield f"data: {json.dumps(error_event)}\n\n"
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