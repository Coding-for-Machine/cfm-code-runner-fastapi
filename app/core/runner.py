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
        if not config: return {"status": "IE", "message": "Language not supported"}

        (isolate.box / config["file"]).write_text(code, encoding="utf-8")

        # 1. Kompilyatsiya
        if config["compile"]:
            c_res = isolate.run(config["compile"])
            if parse_meta(c_res["meta"])["status"] != "OK":
                return {"status": "CE", "message": "Compilation Error", "error": c_res["stderr"]}

        # 2. Ishga tushirish
        run_res = isolate.run(config["run"], stdin_data=test_input)
        meta = parse_meta(run_res["meta"])
        
        status = meta["status"]
        stdout_norm = normalize_output(run_res["stdout"])
        expected_norm = normalize_output(expected_output)

        if status == "OK":
            if stdout_norm == expected_norm: status = "AC"
            else: status = "WA"
        elif status == "TO": status = "TLE"
        elif status == "SG": status = "MLE"
        elif status == "RE": status = "RE"
        else: status = "ERR"

        return {
            "status": status,
            "output": run_res["stdout"],
            "error": run_res["stderr"],
            "time": meta["time"],
            "memory": meta["memory_kb"],
            "exitcode": meta.get("exitcode", 0)
        }
    except Exception as e:
        return {"status": "IE", "message": str(e)}
    finally:
        isolate.cleanup()
        await box_manager.release(box_id)