import asyncio
from typing import AsyncGenerator
from core.runner import execute_code


def wrap_code(user_code: str, wrapper: dict) -> str:
    if not wrapper:
        return user_code
    
    top = wrapper.get("top_code", "")
    bottom = wrapper.get("bottom_code", "")
    return f"{top}\n{user_code}\n{bottom}"


async def stream_execution(
    language: str,
    code: str,
    test_cases: list,
    is_custom_run: bool = False
) -> AsyncGenerator[dict, None]:
    """Test case'larni stream qilib bajarish"""
    
    total = len(test_cases)
    yield {"type": "start", "total": total}
    
    passed = 0
    failed = 0
    
    for idx, test in enumerate(test_cases):
        result = await execute_code(
            language=language,
            code=code,
            test_input=test["input_txt"] or "",
            expected_output=test["output_txt"] or ""
        )
        
        # Agar stdin input kerak bo'lsa
        if result.get("needs_input"):
            yield {
                "type": "needs_input",
                "message": "Code requires input from stdin"
            }
            return
        
        # Custom run uchun output qilish (expected bilan solishtirmasdan)
        if is_custom_run:
            yield {
                "type": "custom",
                "index": idx,
                "result": {
                    "status": result["status"],
                    "output": result.get("output", ""),
                    "error": result.get("error", ""),
                    "execution_time": result.get("time", 0)
                }
            }
            yield {"type": "complete"}
            return
        
        # Submit mode uchun - expected bilan solishtirish
        if result["status"] == "AC":
            passed += 1
        else:
            failed += 1
        
        yield {
            "type": "test",
            "index": idx,
            "is_sample": test.get("is_sample", False),
            "result": result,
            "progress": round((idx + 1) / total * 100, 2),
            "passed": passed,
            "failed": failed
        }
        
        await asyncio.sleep(0.01)
    
    yield {
        "type": "complete",
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "success_rate": round(passed / total * 100, 2) if total > 0 else 0
        }
    }