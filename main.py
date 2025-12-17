import json
import asyncio
import random
from pathlib import Path
from typing import Optional, AsyncGenerator
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, validator
from fastapi.responses import StreamingResponse
import subprocess

# ============= DATABASE =============
from core.db import get_pool

async def get_tests_and_execution(problem_slug: str, language_slug: str):
    """Database'dan problem va test case'larni olish"""
    pool = await get_pool()

    problem = await pool.fetchrow("""
        SELECT id
        FROM problems_problem
        WHERE slug = $1
          AND is_active = true
    """, problem_slug)
    
    if not problem:
        return None

    problem_id = problem["id"]

    language = await pool.fetchrow("""
        SELECT id
        FROM problems_language
        WHERE slug = $1
    """, language_slug)
    
    if not language:
        return None

    language_id = language["id"]

    test_cases = await pool.fetch("""
        SELECT input_txt, output_txt, is_sample
        FROM problems_testcase
        WHERE problem_id = $1
        ORDER BY is_sample DESC, id
    """, problem_id)

    exec_wrapper = await pool.fetchrow("""
        SELECT top_code, bottom_code
        FROM problems_executiontestcase
        WHERE problem_id = $1
          AND language_id = $2
    """, problem_id, language_id)

    return {
        "test_cases": [dict(tc) for tc in test_cases],
        "execution_wrapper": dict(exec_wrapper) if exec_wrapper else None
    }

# ============= BOX MANAGER =============
class BoxManager:
    """Isolate box'larni boshqarish"""
    
    def __init__(self, min_id: int = 0, max_id: int = 999):
        self.min_id = min_id
        self.max_id = max_id
        self._used_boxes = set()
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> int:
        """Bo'sh box_id olish"""
        async with self._lock:
            available = set(range(self.min_id, self.max_id + 1)) - self._used_boxes
            
            if not available:
                raise Exception("Barcha boxlar band! Iltimos biroz kuting.")
            
            box_id = random.choice(list(available))
            self._used_boxes.add(box_id)
            return box_id
    
    async def release(self, box_id: int):
        """Box'ni bo'shatish"""
        async with self._lock:
            self._used_boxes.discard(box_id)

box_manager = BoxManager(min_id=0, max_id=999)

# ============= MODELS =============
class CustomInput(BaseModel):
    value: str = Field(..., max_length=10000)

class RunRequest(BaseModel):
    language_name: str = Field(..., regex="^(python|cpp|java|c)$")
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
    language_name: str = Field(..., regex="^(python|cpp|java|c)$")
    code: str = Field(..., min_length=1, max_length=50000)
    
    @validator('code')
    def validate_code(cls, v):
        dangerous = ['import os', 'import subprocess', '__import__', 'eval(', 'exec(']
        for danger in dangerous:
            if danger in v.lower():
                raise ValueError(f"Xavfli kod: {danger}")
        return v

# ============= ISOLATE WRAPPER =============
class Isolate:
    def __init__(self, box_id: int):
        self.box_id = box_id
        self.base = Path(f"/var/local/lib/isolate/{box_id}")
        self.box = self.base / "box"

    def init(self):
        try:
            subprocess.run(
                ["isolate", f"--box-id={self.box_id}", "--init"],
                check=True,
                capture_output=True,
                timeout=5
            )
        except subprocess.TimeoutExpired:
            raise Exception("Isolate init timeout")
        except subprocess.CalledProcessError as e:
            raise Exception(f"Isolate init failed: {e.stderr.decode()}")

    def cleanup(self):
        try:
            subprocess.run(
                ["isolate", f"--box-id={self.box_id}", "--cleanup"],
                capture_output=True,
                timeout=5
            )
        except:
            pass

    def run(self, cmd: list, stdin_data: str = "") -> dict:
        meta = self.box / "meta.txt"
        
        if stdin_data:
            (self.box / "input.txt").write_text(stdin_data, encoding="utf-8")
        
        isolate_cmd = [
            "isolate",
            f"--box-id={self.box_id}",
            "--run",
            "--processes=1",
            "--no-network",
            "--time=2",
            "--wall-time=3",
            "--mem=262144",
            "--fsize=10240",
            "--stack=8192",
            "--stdin=input.txt",
            "--stdout=out.txt",
            "--stderr=err.txt",
            f"--meta={meta}",
            "--",
        ] + cmd
        
        try:
            subprocess.run(isolate_cmd, cwd=self.base, timeout=5, check=False)
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": "Time Limit Exceeded",
                "meta": "status:TO\n"
            }
        
        return {
            "stdout": (self.box / "out.txt").read_text(errors="ignore").strip() if (self.box / "out.txt").exists() else "",
            "stderr": (self.box / "err.txt").read_text(errors="ignore").strip() if (self.box / "err.txt").exists() else "",
            "meta": meta.read_text(errors="ignore") if meta.exists() else ""
        }

# ============= LANGUAGE CONFIGS =============
LANGUAGE_CONFIGS = {
    "python": {
        "file": "solution.py",
        "compile": None,
        "run": ["/usr/bin/python3", "solution.py"]
    },
    "cpp": {
        "file": "solution.cpp",
        "compile": ["/usr/bin/g++", "-O2", "-std=c++17", "-o", "solution", "solution.cpp"],
        "run": ["./solution"]
    },
    "c": {
        "file": "solution.c",
        "compile": ["/usr/bin/gcc", "-O2", "-o", "solution", "solution.c"],
        "run": ["./solution"]
    },
    "java": {
        "file": "Solution.java",
        "compile": ["/usr/bin/javac", "Solution.java"],
        "run": ["/usr/bin/java", "Solution"]
    }
}

# ============= CODE WRAPPER =============
def wrap_code(user_code: str, wrapper: dict, language: str) -> str:
    """Wrapper code bilan user code'ni birlashtirish"""
    if not wrapper:
        return user_code
    
    top = wrapper.get("top_code", "")
    bottom = wrapper.get("bottom_code", "")
    
    # Indent user code (Python uchun)
    if language == "python" and top:
        lines = user_code.split("\n")
        indented = "\n".join(f"    {line}" if line.strip() else "" for line in lines)
        return f"{top}\n{indented}\n{bottom}"
    
    return f"{top}\n{user_code}\n{bottom}"

# ============= EXECUTION =============
async def execute_code(
    language: str,
    code: str,
    test_input: str,
    expected_output: str
) -> dict:
    """Bitta test case uchun kodni bajarish"""
    
    box_id = None
    isolate = None
    
    try:
        box_id = await box_manager.acquire()
        isolate = Isolate(box_id)
        isolate.init()
        
        config = LANGUAGE_CONFIGS.get(language)
        if not config:
            return {"error": "Noma'lum til", "status": "IE"}
        
        code_file = isolate.box / config["file"]
        code_file.write_text(code, encoding="utf-8")
        
        # Kompilyatsiya
        if config["compile"]:
            result = isolate.run(config["compile"])
            if "error" in result["stderr"].lower() or "status:RE" in result["meta"]:
                return {
                    "status": "CE",
                    "error": result["stderr"][:500],
                    "output": ""
                }
        
        # Bajarish
        result = isolate.run(config["run"], stdin_data=test_input)
        
        # Natijani tahlil
        meta = result["meta"]
        if "status:TO" in meta or "time-wall" in meta:
            return {"status": "TLE", "error": "Time Limit Exceeded", "output": ""}
        elif "status:RE" in meta:
            return {"status": "RE", "error": result["stderr"][:500], "output": ""}
        elif "status:SG" in meta:
            return {"status": "RTE", "error": "Runtime Error", "output": ""}
        
        output = result["stdout"].strip()
        expected = expected_output.strip()
        
        if output == expected:
            return {"status": "AC", "output": output, "error": ""}
        else:
            return {
                "status": "WA",
                "output": output[:500],
                "expected": expected[:500],
                "error": ""
            }
    
    except Exception as e:
        return {"status": "IE", "error": str(e)[:500], "output": ""}
    
    finally:
        if isolate:
            isolate.cleanup()
        if box_id is not None:
            await box_manager.release(box_id)

# ============= STREAMING =============
async def stream_execution(
    language: str,
    code: str,
    test_cases: list,
    wrapper: dict = None
) -> AsyncGenerator[dict, None]:
    """Test case'larni stream qilib bajarish"""
    
    # Wrapper bilan kod birlashtirish
    final_code = wrap_code(code, wrapper, language)
    
    total = len(test_cases)
    yield {"type": "start", "total": total}
    
    passed = 0
    failed = 0
    
    for idx, test in enumerate(test_cases):
        result = await execute_code(
            language=language,
            code=final_code,
            test_input=test["input_txt"] or "",
            expected_output=test["output_txt"] or ""
        )
        
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

# ============= API ROUTER =============
api = APIRouter(prefix="/code", tags=["Code Execution"])

@api.post("/run/{problem_slug}")
async def run_code(problem_slug: str, request: RunRequest):
    """Custom input bilan kodni test qilish (faqat sample test cases)"""
    
    # Database'dan ma'lumot olish
    data = await get_tests_and_execution(problem_slug, request.language_name)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem yoki til topilmadi"
        )
    
    # Faqat sample test case'lar
    sample_tests = [tc for tc in data["test_cases"] if tc.get("is_sample", False)]
    
    if not sample_tests and not request.custom_input:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem yoki til topilmadi"
        )
    
    if not data["test_cases"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
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