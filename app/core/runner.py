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
    """
    Kodni xavfsiz sandbox'da bajarish (Judge0-style)
    
    Args:
        language: Dasturlash tili (python, cpp, java, ...)
        code: Bajariladigan kod
        test_input: STDIN uchun input
        expected_output: Kutilgan output (bo'sh bo'lsa faqat bajarish)
    
    Returns:
        dict: Bajarilish natijasi
            - status: OK/RE/TO/CE/...
            - time: CPU vaqti (soniyalarda)
            - memory_kb: Xotira (KB)
            - stdout: Dastur output'i
            - stderr: Xato xabarlari
            - is_accepted: Expected bilan mos kelishi (True/False)
    
    Flow:
        1. Box olish (pool'dan)
        2. Init qilish
        3. Kod yozish
        4. Kompilyatsiya (agar kerak bo'lsa)
        5. Bajarish
        6. Output solishtirish
        7. Cleanup va box qaytarish
    """
    
    box_id = None
    isolate = None

    try:
        # ========== 1. BOX OLISH ==========
        # BoxManager pool'dan bo'sh box_id oladi
        # Agar barcha boxlar band bo'lsa, Exception raise qiladi
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

        # ========== 3. KOD YOZISH ==========
        # Isolate sandbox ichida kod faylini yaratish
        code_file = isolate.box / config["file"]
        code_file.write_text(code, encoding="utf-8")

        # ========== 4. KOMPILYATSIYA (agar kerak bo'lsa) ==========
        # C/C++/Java/Go kabi kompilyatsiya talab qiluvchi tillar uchun
        if config["compile"]:
            compile_result = isolate.run(config["compile"])
            
            # Kompilyatsiya xatosini tekshirish
            # stderr mavjud yoki meta'da RE statusi bo'lsa = CE
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

        # ========== 5. BAJARISH ==========
        # Dasturni test_input bilan ishga tushirish
        run_result = isolate.run(config["run"], stdin_data=test_input)
        
        # Meta'ni parse qilish (time, memory, status, ...)
        meta = parse_meta(run_result["meta"])
        
        stdout = run_result["stdout"]
        stderr = run_result["stderr"]

        # ========== 6. OUTPUT SOLISHTIRISH ==========
        # Faqat expected_output berilgan bo'lsa (Submit mode)
        is_accepted = False
        
        if meta["status"] == "OK" and expected_output:
            # Whitespace farqlarini inobatga olmasdan solishtirish
            normalized_output = normalize_output(stdout)
            normalized_expected = normalize_output(expected_output)
            
            if normalized_output == normalized_expected:
                is_accepted = True

        # ========== 7. NATIJANI QAYTARISH ==========
        # Judge0-style result format
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
        # Kutilmagan xatolar (Internal Error)
        # Bu juda kamdan-kam sodir bo'lishi kerak
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
        # ========== 8. CLEANUP ==========
        # Har doim cleanup va box'ni qaytarish (hatto exception bo'lsa ham)
        if isolate:
            isolate.cleanup()
        if box_id is not None:
            await box_manager.release(box_id)


# ========== QANDAY ISHLAYDI ==========
"""
1. REQUEST KELADI:
   POST /api/run/two-sum
   {
     "language_name": "python",
     "code": "n = int(input())\nprint(n * 2)",
     "custom_input": {"value": "5"}
   }

2. EXECUTE_CODE CHAQIRILADI:
   - Box olish: box_manager.acquire() → box_id=427
   - Init: isolate --box-id=427 --init
   - Kod yozish: /var/local/lib/isolate/427/box/solution.py
   - Bajarish: isolate --run ... python3 solution.py
   - Meta parse: time=0.029, status=OK, exitcode=0
   - Output: "10"

3. NATIJA QAYTARILADI:
   {
     "status": "OK",
     "message": "Accepted",
     "time": 0.029,
     "stdout": "10",
     "is_accepted": true
   }

4. CLEANUP:
   - isolate --box-id=427 --cleanup
   - box_manager.release(427)
"""


# ========== JUDGE0 BILAN TAQQOSLASH ==========
"""
✅ ADVANTAGES (Bizning versiya):
- Lightweightroq (faqat Python + Isolate)
- Ko'proq customizable
- To'g'ridan-to'g'ri control
- Kodni o'zgartirish oson

✅ JUDGE0 FEATURES (biz ham qo'llab-quvvatlaymiz):
- Multiple languages ✓
- Time/Memory limits ✓
- Compilation ✓
- Status codes (AC/WA/TLE/RE/CE) ✓
- Output normalization ✓
- Parallel execution ✓ (1000 boxes)

⚠️ JUDGE0 QANDAY YAXSHI:
- API Gateway
- Queue management (RabbitMQ)
- Database integration
- Web UI
- Callback system
- More languages (40+)

📊 NATIJA:
Bizning versiya - bu JUDGE0'ning "core execution engine" qismi.
Judge0 = Bizning kod + Queue + API + UI + Database
"""