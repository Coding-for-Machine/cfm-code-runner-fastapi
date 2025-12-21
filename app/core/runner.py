import asyncio
from core.isolate import Isolate, LANGUAGE_CONFIGS
from core.box_manager import box_manager

def parse_meta(meta: str) -> dict:
    data = {}
    for line in meta.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            data[k.strip()] = v.strip()
    
    status = data.get("status", "OK")
    return {
        "status": status,
        "time": float(data.get("time", 0)),
        "memory_kb": int(data.get("max-rss", 0)),
        "exitcode": int(data.get("exitcode", -1))
    }

def normalize_output(text: str) -> str:
    return "\n".join(line.strip() for line in text.strip().splitlines() if line.strip())
async def execute_code(language: str, code: str, test_input: str, expected_output: str = "") -> dict:
    box_id = await box_manager.acquire()
    isolate = Isolate(box_id)
    try:
        isolate.init()
        config = LANGUAGE_CONFIGS.get(language)
        if not config: 
            return {"status": "IE", "message": "Internal Error: Unsupported Language"}

        (isolate.box / config["file"]).write_text(code, encoding="utf-8")

        # 1. Kompilyatsiya bosqichi
        if config["compile"]:
            c_res = isolate.run(config["compile"], env_vars=config.get("env", []))
            c_meta = parse_meta(c_res["meta"])
            if c_meta["status"] != "OK":
                return {
                    "status": "CE", 
                    "message": "Compilation Error", 
                    "stderr": c_res["stderr"],
                    "is_accepted": False
                }

        # 2. Ishga tushirish bosqichi
        run_res = isolate.run(config["run"], stdin_data=test_input, env_vars=config.get("env", []))
        meta = parse_meta(run_res["meta"])
        
        status = meta["status"]
        is_accepted = False
        message = ""

        # 3. Status va Xabarlarni aniqlash
        if status == "OK":
            stdout_norm = normalize_output(run_res["stdout"])
            expected_norm = normalize_output(expected_output)
            
            if stdout_norm == expected_norm:
                status = "AC"
                message = "Accepted"
                is_accepted = True
            else:
                status = "WA"
                message = "Wrong Answer"
                is_accepted = False
        
        elif status == "TO":
            status = "TLE"
            message = "Time Limit Exceeded"
        
        elif status == "SG":
            # Ko'pincha Memory Limit SG (Signal) sifatida qaytadi
            status = "MLE" 
            message = "Memory Limit Exceeded"
            
        elif status == "RE":
            status = "RE"
            message = f"Runtime Error (Exit code: {meta['exitcode']})"
            
        else:
            status = "ERR"
            message = "Internal Sandbox Error"

        return {
            "status": status, 
            "message": message, 
            "is_accepted": is_accepted,
            "output": run_res["stdout"], 
            "error": run_res["stderr"],
            "time": meta["time"], 
            "memory": meta["memory_kb"],
            "exitcode": meta.get("exitcode", 0),
        }
        
    except Exception as e:
        return {
            "status": "IE", 
            "message": f"System Error: {str(e)}",
            "is_accepted": False
        }
    finally:
        isolate.cleanup()
        await box_manager.release(box_id)
