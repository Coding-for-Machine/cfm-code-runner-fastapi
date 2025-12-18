import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
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
    is_sample: bool = False

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
    - Run mode: custom_input mavjud (test_cases bilan yoki bo'lmasdan)
    - Submit mode: custom_input yo'q, faqat test_cases (DB + user test cases)
    """
    
    async def event_generator():
        try:
            # DB dan ma'lumotlarni olish
            data = await get_tests_and_execution(problem_slug, request.language_name)
            
            # ====== RUN MODE (custom_input mavjud) ======
            if request.custom_input:
                # Wrapper bor/yo'qligini tekshirish
                has_wrapper = data and data.get("execution_wrapper")
                
                if has_wrapper:
                    final_code = wrap_code(request.code, data["execution_wrapper"], request.language_name)
                else:
                    final_code = request.code
                
                # Custom input test case
                custom_test = {
                    "input_txt": request.custom_input.value,
                    "output_txt": "",
                    "is_sample": False
                }
                
                # Barcha test cases'larni yig'ish (custom + user test cases)
                run_tests = [custom_test]
                if request.test_cases:
                    run_tests.extend([{
                        "input_txt": tc.input_txt,
                        "output_txt": tc.output_txt,
                        "is_sample": tc.is_sample
                    } for tc in request.test_cases])
                
                # Stream execution
                async for event in stream_execution(
                    language=request.language_name,
                    code=final_code,
                    test_cases=run_tests,
                    is_custom_run=True
                ):
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            
            # ====== SUBMIT MODE (custom_input yo'q) ======
            else:
                if not data or not data.get("test_cases"):
                    raise HTTPException(status_code=400, detail="Test cases not found for this problem")
                
                # DB test cases + user test cases (agar bor bo'lsa)
                all_test_cases = data["test_cases"]
                if request.test_cases:
                    all_test_cases.extend([{
                        "input_txt": tc.input_txt,
                        "output_txt": tc.output_txt,
                        "is_sample": tc.is_sample
                    } for tc in request.test_cases])
                
                # Wrapper bilan kod birlashtirish
                final_code = wrap_code(request.code, data["execution_wrapper"], request.language_name)
                
                # Submit stream execution
                async for event in stream_execution(
                    language=request.language_name,
                    code=final_code,
                    test_cases=all_test_cases,
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