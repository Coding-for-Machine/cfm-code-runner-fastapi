import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from fastapi.responses import StreamingResponse
from core.runner import execute_code
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


@api.post("/run")
async def run_code_endpoint(request: RunRequest):
    """
    RUN MODE:
    - Wrapper ishlatilmaydi (faqat user kodi).
    - DB dan test olinmaydi.
    - Faqat frontenddan kelgan test_cases va custom_input ishlatiladi.
    """
    async def run_generator():
        # Testlarni yig'ish: Custom input (agar bo'lsa) + qo'shimcha testlar
        run_tests = []
        if request.custom_input:
            run_tests.append({
                "input_txt": request.custom_input.value,
                "output_txt": "",
                "is_sample": False
            })
        
        if request.test_cases:
            for tc in request.test_cases:
                run_tests.append({
                    "input_txt": tc.input_txt,
                    "output_txt": tc.output_txt,
                    "is_sample": tc.is_sample
                })

        if not run_tests:
            # Agar hech qanday input bo'lmasa, bo'sh input bilan bitta test
            run_tests.append({"input_txt": "", "output_txt": "", "is_sample": False})

        async for event in stream_execution(
            language=request.language_name,
            code=request.code, # Wrapper yo'q
            test_cases=run_tests,
            is_custom_run=True
        ):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(run_generator(), media_type="text/event-stream")


@api.post("/submit/{problem_slug}")
async def submit_code_endpoint(problem_slug: str, request: RunRequest):
    """
    SUBMIT MODE:
    - DB dan testlar va wrapper olinadi.
    - Frontenddan kelgan testlar DB testlariga qo'shiladi.
    - Kod wrapper bilan o'raladi.
    """
    # DB dan ma'lumotlarni olish
    data = await get_tests_and_execution(problem_slug, request.language_name)
    if not data:
        raise HTTPException(status_code=404, detail="Problem yoki Language topilmadi")

    async def submit_generator():
        # 1. Kodni wrapper bilan o'rash
        final_code = wrap_code(request.code, data.get("execution_wrapper"))
        
        # 2. Testlarni birlashtirish: DB testlari + Client testlari
        all_tests = data["test_cases"].copy()
        if request.test_cases:
            for tc in request.test_cases:
                all_tests.append({
                    "input_txt": tc.input_txt,
                    "output_txt": tc.output_txt,
                    "is_sample": tc.is_sample
                })

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
    """Box status monitoring"""
    from core.runner import box_manager
    
    return {
        "total_boxes": 1000,
        "used_boxes": len(box_manager._used_boxes),
        "available": 1000 - len(box_manager._used_boxes)
    }