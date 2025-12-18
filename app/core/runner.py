import re
from core.box_manager import BoxManager
from .isolate import LANGUAGE_CONFIGS, Isolate

box_manager = BoxManager(min_id=0, max_id=999)


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
            return {"error": "Unknown language", "status": "IE"}
        
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
        
        # Meta tahlil
        meta = result["meta"]
        time_match = re.search(r'time:([\d.]+)', meta)
        exec_time = float(time_match.group(1)) if time_match else 0
        
        # TLE check
        if "status:TO" in meta or "time-wall" in meta:
            return {
                "status": "TLE",
                "error": "Time Limit Exceeded",
                "output": "",
                "time": exec_time
            }
        
        # Runtime Error check
        if "status:RE" in meta:
            stderr = result["stderr"][:500]
            # EOFError yoki input-related xatoliklarni aniqlash
            if any(err in stderr for err in ["EOFError", "InputMismatchException", "NoSuchElementException", "EOF"]):
                return {
                    "status": "NEEDS_INPUT",
                    "needs_input": True,
                    "error": "Program is waiting for input",
                    "output": result["stdout"][:200],
                    "time": exec_time
                }
            return {
                "status": "RE",
                "error": stderr,
                "output": "",
                "time": exec_time
            }
        
        # Signal/Crash
        if "status:SG" in meta:
            return {
                "status": "RTE",
                "error": "Runtime Error (Signal)",
                "output": "",
                "time": exec_time
            }
        
        output = result["stdout"].strip()
        
        # Agar expected_output bo'sh bo'lsa (custom run), faqat output qaytarish
        if not expected_output:
            return {
                "status": "OK",
                "output": output[:1000],
                "error": result["stderr"][:200] if result["stderr"] else "",
                "time": exec_time
            }
        
        # Submit mode - solishtirish
        expected = expected_output.strip()
        
        if output == expected:
            return {
                "status": "AC",
                "output": output,
                "error": "",
                "time": exec_time
            }
        else:
            return {
                "status": "WA",
                "output": output[:500],
                "expected": expected[:500],
                "error": "",
                "time": exec_time
            }
    
    except Exception as e:
        return {
            "status": "IE",
            "error": str(e)[:500],
            "output": ""
        }
    
    finally:
        if isolate:
            isolate.cleanup()
        if box_id is not None:
            await box_manager.release(box_id)