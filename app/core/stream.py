import asyncio
from typing import AsyncGenerator
from core.runner import execute_code


def wrap_code(user_code: str, wrapper: dict) -> str:
    """User code'ni wrapper bilan birlashtirish"""
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
    """
    Test case'larni stream qilib bajarish
    
    Args:
        language: Dasturlash tili
        code: Bajarish uchun kod
        test_cases: Test case'lar ro'yxati
        is_custom_run: Custom run rejimi (True) yoki Submit (False)
    
    Yields:
        dict: Bajarilish jarayoni haqida ma'lumotlar
    """
    
    total = len(test_cases)
    yield {"type": "start", "total": total}
    
    passed = 0
    failed = 0
    
    for idx, test in enumerate(test_cases):
        # Test case'ni bajarish
        result = await execute_code(
            language=language,
            code=code,
            test_input=test.get("input_txt", ""),
            expected_output=test.get("output_txt", "")
        )
        
        # NEEDS_INPUT holatini tekshirish (birinchi navbatda!)
        if result.get("status") == "NEEDS_INPUT":
            yield {
                "type": "needs_input",
                "message": "Program requires input from stdin",
                "index": idx,
                "error": result.get("error", "")
            }
            return
        
        # ====== CUSTOM RUN MODE ======
        if is_custom_run:
            yield {
                "type": "custom",
                "index": idx,
                "result": {
                    "status": result["status"],
                    "output": result.get("output", ""),
                    "error": result.get("error", ""),
                    "time": result.get("time", 0)
                }
            }
            continue
        
        # ====== SUBMIT MODE ======
        # Passed/Failed hisobi
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
        
        # Kichik kutish (stream effect uchun)
        await asyncio.sleep(0.01)
    
    # Yakuniy natija
    yield {
        "type": "complete",
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "success_rate": round(passed / total * 100, 2) if total > 0 else 0
        } if not is_custom_run else None
    }