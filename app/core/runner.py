import re
from core.box_manager import BoxManager
from core.isolate import LANGUAGE_CONFIGS, Isolate

# Global box manager
box_manager = BoxManager(min_id=0, max_id=999)


async def execute_code(
    language: str,
    code: str,
    test_input: str,
    expected_output: str
) -> dict:
    """
    Bitta test case uchun kodni bajarish
    
    Args:
        language: Dasturlash tili
        code: Bajarish uchun kod
        test_input: Input ma'lumotlar
        expected_output: Kutilgan output (bo'sh bo'lsa custom run)
    
    Returns:
        dict: Bajarilish natijasi
    """
    
    box_id = None
    isolate = None
    
    try:
        # Box olish
        box_id = await box_manager.acquire()
        isolate = Isolate(box_id)
        isolate.init()
        
        # Til konfiguratsiyasini olish
        config = LANGUAGE_CONFIGS.get(language)
        if not config:
            return {
                "status": "IE",
                "error": f"Unknown language: {language}",
                "output": ""
            }
        
        # Kod faylini yozish
        code_file = isolate.box / config["file"]
        code_file.write_text(code, encoding="utf-8")
        
        # ====== KOMPILYATSIYA (agar kerak bo'lsa) ======
        if config["compile"]:
            result = isolate.run(config["compile"])
            
            # Kompilyatsiya xatolarini tekshirish
            if result["stderr"] or "status:RE" in result["meta"]:
                return {
                    "status": "CE",
                    "error": result["stderr"][:1000],
                    "output": ""
                }
        
        # ====== BAJARISH ======
        result = isolate.run(config["run"], stdin_data=test_input)
        
        # Meta ma'lumotlarni tahlil qilish
        meta = result["meta"]
        time_match = re.search(r'time:([\d.]+)', meta)
        exec_time = float(time_match.group(1)) if time_match else 0
        
        # ====== TIME LIMIT EXCEEDED ======
        if "status:TO" in meta or "time-wall" in meta:
            return {
                "status": "TLE",
                "error": "Time Limit Exceeded",
                "output": result["stdout"][:200],
                "time": exec_time
            }
        
        # ====== RUNTIME ERROR (RE) ======
        if "status:RE" in meta or result.get("exitcode", 0) != 0:
            stderr = result["stderr"]
            
            # EOFError va input-related xatoliklarni aniqlash
            input_errors = [
                "EOFError",
                "InputMismatchException", 
                "NoSuchElementException",
                "EOF when reading a line",
                "Scanner is closed",
                "no line found"
            ]
            
            if any(err in stderr for err in input_errors):
                return {
                    "status": "NEEDS_INPUT",
                    "error": "Program is waiting for input, but no input was provided",
                    "output": result["stdout"][:500],
                    "time": exec_time
                }
            
            return {
                "status": "RE",
                "error": stderr[:1000],
                "output": result["stdout"][:500],
                "time": exec_time
            }
        
        # ====== SIGNAL/CRASH ======
        if "status:SG" in meta:
            return {
                "status": "RTE",
                "error": "Runtime Error (Signal/Crash)",
                "output": result["stdout"][:500],
                "time": exec_time
            }
        
        # ====== OUTPUT TAHLIL ======
        output = result["stdout"].strip()
        
        # Custom run (expected_output bo'sh)
        if not expected_output:
            return {
                "status": "OK",
                "output": output[:5000],
                "error": result["stderr"][:500] if result["stderr"] else "",
                "time": exec_time
            }
        
        # ====== SUBMIT MODE - OUTPUT SOLISHTIRISH ======
        expected = expected_output.strip()
        
        if output == expected:
            return {
                "status": "AC",
                "output": output[:1000],
                "error": "",
                "time": exec_time
            }
        else:
            # Qo'shimcha tekshiruv: whitespace farqlari
            output_normalized = " ".join(output.split())
            expected_normalized = " ".join(expected.split())
            
            if output_normalized == expected_normalized:
                return {
                    "status": "AC",
                    "output": output[:1000],
                    "error": "",
                    "time": exec_time,
                    "note": "Accepted with whitespace differences"
                }
            
            return {
                "status": "WA",
                "output": output[:1000],
                "expected": expected[:1000],
                "error": "",
                "time": exec_time
            }
    
    except Exception as e:
        return {
            "status": "IE",
            "error": f"Internal error: {str(e)[:1000]}",
            "output": ""
        }
    
    finally:
        # Cleanup
        if isolate:
            isolate.cleanup()
        if box_id is not None:
            await box_manager.release(box_id)