import re
from core.box_manager import BoxManager
from core.isolate import LANGUAGE_CONFIGS, Isolate

# Global box manager - 1000 ta parallel sandbox (0-999)
box_manager = BoxManager(min_id=0, max_id=999)


def parse_meta(meta: str) -> dict:
    """
    Isolate meta faylini parse qilish
    
    Meta format:
        time:0.059              - CPU vaqti (soniyalarda)
        time-wall:0.067         - Real vaqt (soniyalarda)
        max-rss:9320            - Maksimal xotira (KB)
        csw-voluntary:4         - Voluntary context switches
        csw-forced:46           - Forced context switches
        exitcode:0              - Exit code (0 = success)
        status:RE/TO/SG/XX      - Isolate statusi
    
    Returns:
        dict: Parse qilingan ma'lumotlar
    """
    data = {}
    
    for line in meta.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    
    # Status xabarlari (Judge0-style)
    status_messages = {
        "OK": "Accepted",                    # Muvaffaqiyatli bajarildi
        "RE": "Runtime Error",               # Runtime xato (exitcode != 0)
        "TO": "Time Limit Exceeded",         # Vaqt limiti oshdi
        "SG": "Runtime Error (Signal)",      # Signal (segfault, etc)
        "XX": "Internal Error",              # Isolate ichki xato
        "CE": "Compilation Error",           # Kompilyatsiya xatosi
        "MLE": "Memory Limit Exceeded",      # Xotira limiti oshdi
    }
    
    status = data.get("status", "OK")
    message = status_messages.get(status, "Unknown Error")
    
    return {
        "status": status,
        "message": message,
        "time": float(data.get("time", 0)),
        "wall_time": float(data.get("time-wall", 0)),
        "memory_kb": int(data.get("max-rss", 0)),
        "exitcode": int(data.get("exitcode", -1)),
    }


def normalize_output(text: str) -> str:
    """
    Output'ni normalizatsiya qilish (Judge0-style)
    
    - Trailing whitespace'larni olib tashlash
    - Bo'sh qatorlarni tozalash
    - Har bir qatorni trim qilish
    
    Bu WA (Wrong Answer) false positive'larini kamaytiradi
    
    Args:
        text: Normalize qilinadigan matn
    
    Returns:
        str: Normalize qilingan matn
    """
    return "\n".join(
        line.rstrip() for line in text.strip().splitlines()
    )


async def execute_code(
    language: str,
    code: str,
    test_input: str,
    expected_output: str = ""
) -> dict:
    try:
        box_id = await box_manager.acquire()
        isolate = Isolate(box_id)
        isolate.init()

        # ========== 2. TIL KONFIGURATSIYASI ==========
        config = LANGUAGE_CONFIGS.get(language)
        if not config:
            return {
                "status": "IE",
                "message": "Internal Error",
                "error": f"Unsupported language: {language}",
                "stdout": "",
                "stderr": "",
            }

        code_file = isolate.box / config["file"]
        code_file.write_text(code, encoding="utf-8")

        if config["compile"]:
            compile_result = isolate.run(config["compile"])
            
            if compile_result["stderr"] or "status:RE" in compile_result["meta"]:
                return {
                    "status": "CE",
                    "message": "Compilation Error",
                    "error": compile_result["stderr"][:2000],
                    "stdout": "",
                    "stderr": compile_result["stderr"][:2000],
                    "time": 0,
                    "memory_kb": 0,
                }
        run_result = isolate.run(config["run"], stdin_data=test_input)
        
        meta = parse_meta(run_result["meta"])
        
        stdout = run_result["stdout"]
        stderr = run_result["stderr"]

        is_accepted = False
        
        if meta["status"] == "OK" and expected_output:
            normalized_output = normalize_output(stdout)
            normalized_expected = normalize_output(expected_output)
            
            if normalized_output == normalized_expected:
                is_accepted = True

        return {
            "status": meta["status"],           # OK/RE/TO/CE/...
            "message": meta["message"],         # Human-readable xabar
            "language": language,               # python/cpp/java/...
            "time": meta["time"],               # CPU vaqti (soniya)
            "wall_time": meta["wall_time"],     # Real vaqt (soniya)
            "memory_kb": meta["memory_kb"],     # Xotira (KB)
            "exitcode": meta["exitcode"],       # Dastur exit code
            "stdout": stdout[:5000],            # Output (max 5000 char)
            "stderr": stderr[:2000],            # Xatolar (max 2000 char)
            "input": test_input[:1000],         # Input (debug uchun)
            "expected_output": expected_output[:1000],  # Kutilgan output
            "is_accepted": is_accepted,         # True = AC, False = WA
        }

    except Exception as e:
        return {
            "status": "IE",
            "message": "Internal Error",
            "error": f"Unexpected error: {str(e)}",
            "stdout": "",
            "stderr": "",
            "time": 0,
            "memory_kb": 0,
        }

    finally:
        if isolate:
            isolate.cleanup()
        if box_id is not None:
            await box_manager.release(box_id)
