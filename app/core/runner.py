
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
