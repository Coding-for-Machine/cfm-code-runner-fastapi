import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from fastapi.responses import StreamingResponse
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
async def run_code_endpoint(problem_slug: str, request: RunRequest):
    async def run_generator():
        run_tests = []
        if request.custom_input:
            run_tests.append({"input_txt": request.custom_input.value, "output_txt": "", "is_sample": False})
        
        if request.test_cases:
            for tc in request.test_cases:
                run_tests.append({"input_txt": tc.input_txt, "output_txt": tc.output_txt, "is_sample": tc.is_sample})

        if not run_tests:
            run_tests.append({"input_txt": "", "output_txt": "", "is_sample": False})

        # DB'dan wrapper olish
        data = await get_tests_and_execution(problem_slug, request.language_name)
        final_code = wrap_code(request.code, data.get("execution_wrapper")) if data else request.code

        async for event in stream_execution(
            language=request.language_name,
            code=final_code,
            test_cases=run_tests,
            is_custom_run=True
        ):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(run_generator(), media_type="text/event-stream")

@api.post("/submit/{problem_slug}")
async def submit_code_endpoint(problem_slug: str, request: RunRequest):
    data = await get_tests_and_execution(problem_slug, request.language_name)
    if not data or not data.get("test_cases"):
        raise HTTPException(status_code=404, detail="Testlar topilmadi")

    async def submit_generator():
        final_code = wrap_code(request.code, data.get("execution_wrapper"))
        all_tests = data["test_cases"] # Faqat DB testlari
        print("test--", all_tests)
        async for event in stream_execution(
            language=request.language_name,
            code=final_code,
            test_cases=all_tests,
            is_custom_run=False
        ):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(submit_generator(), media_type="text/event-stream")

@api.get("/status")
async def get_status():
    from core.runner import box_manager
    return {
        "total_boxes": 1000,
        "used_boxes": len(box_manager._used_boxes),
        "available": 1000 - len(box_manager._used_boxes)
    }

@api.get("/languages")
async def get_languages():
    return [
        {"language_name": "python", "slug": "python"},
        {"language_name": "golang", "slug": "go"},
        {"language_name": "cpp", "slug": "cpp"},
        {"language_name": "JavaScript", "slug": "javascript"},
        {"language_name": "TypeScript", "slug": "typescript"},
    ]
