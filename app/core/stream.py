import asyncio
import json
from typing import AsyncGenerator
from core.runner import execute_code

def wrap_code(user_code: str, wrapper: dict) -> str:
    if not wrapper: return user_code
    top = wrapper.get("top_code", "")
    bottom = wrapper.get("bottom_code", "")
    return f"{top}\n{user_code}\n{bottom}"

async def stream_execution(
    language: str,
    code: str,
    test_cases: list,
    is_custom_run: bool = False
) -> AsyncGenerator[dict, None]:
    total = len(test_cases)
    yield {"type": "start", "total": total}
    
    passed, failed = 0, 0
    
    for idx, test in enumerate(test_cases):
        print(f"test-{idx}---test")
        result = await execute_code(
            language=language,
            code=code,
            test_input=test.get("input_txt", ""),
            expected_output=test.get("output_txt", "")
        )
        
        if result.get("status") == "NEEDS_INPUT":
            yield {"type": "error", "message": "Programma input kutyapti", "index": idx}
            return

        if is_custom_run:
            # RUN rejimida har doim outputni qaytaramiz
            yield {
                "type": "custom",
                "index": idx,
                "status": result["status"],
                "input": test.get("input_txt"),
                "output": result.get("output"),
                "expected": test.get("output_txt"),
                "error": result.get("error"),
                "time": result.get("time")
            }
        else:
            # SUBMIT rejimida AC/WA hisobini yuritamiz
            if result["status"] == "AC": passed += 1
            else: failed += 1
            
            yield {
                "type": "test",
                "index": idx,
                "is_sample": test.get("is_sample", False),
                "status": result["status"],
                "input": test.get("input_txt"),
                "output": result.get("output"),
                "expected": test.get("output_txt"),
                "error": result.get("error"),
                "time": result.get("time")
            }
            # if result["status"] != "AC": break
            
        await asyncio.sleep(0.01)
    
    yield {
        "type": "complete",
        "summary": {
            "total": total, "passed": passed, "failed": failed,
            "success_rate": round(passed/total*100, 2) if total > 0 else 0
        } if not is_custom_run else None
    }
