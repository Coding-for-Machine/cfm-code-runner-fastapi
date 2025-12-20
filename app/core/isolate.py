# import subprocess
# from pathlib import Path
# from typing import Dict, List, Optional
# import os
# import shutil

# # =====================================================
# # TILLAR SOZLAMALARI
# # =====================================================
# LANGUAGE_CONFIGS: Dict[str, Dict] = {
#     "python": {
#         "file": "solution.py",
#         "compile": None,
#         "run": ["/usr/bin/python3", "solution.py"],
#     },
#     "javascript": {
#         "file": "solution.js",
#         "compile": None,
#         "run": ["/usr/bin/node", "solution.js"],
#     },
#     "typescript": {
#         "file": "solution.ts",
#         "compile": ["/usr/bin/node", "/usr/bin/tsc", "solution.ts", "--target", "ES2020", "--module", "CommonJS"],
#         "run": ["/usr/bin/node", "solution.js"],
#     },
#     "go": {
#         "file": "solution.go",
#         # Docker ichida Go odatda /usr/bin/go da bo'ladi
#         "compile": ["/usr/bin/go", "build", "-o", "solution", "solution.go"],
#         "run": ["./solution"],
#         "env": ["GOCACHE=/tmp", "HOME=/tmp"]
#     },
#     "cpp": {
#         "file": "solution.cpp",
#         "compile": ["/usr/bin/g++", "-O2", "solution.cpp", "-o", "solution"],
#         "run": ["./solution"],
#     },
#     "java": {
#         "file": "Solution.java",
#         "compile": ["/usr/bin/javac", "-J-Xms128M", "-J-Xmx512M", "Solution.java"],
#         "run": ["/usr/bin/java", "-Xmx512M", "Solution"],
#     },
# }

# class Isolate:
#     def __init__(self, box_id: int):
#         self.box_id = box_id
#         # Docker ichida isolate bazasi
#         self.base = Path(f"/var/local/lib/isolate/{box_id}")
#         self.box = self.base / "box"

#     def init(self) -> None:
#         # 1. Tozalash
#         subprocess.run(["isolate", f"--box-id={self.box_id}", "--cleanup"], capture_output=True)
#         if self.base.exists():
#             shutil.rmtree(self.base)
        
#         # 2. Init
#         result = subprocess.run(
#             ["isolate", f"--box-id={self.box_id}", "--init"], 
#             capture_output=True, text=True
#         )
#         if result.returncode != 0:
#             raise RuntimeError(f"Isolate init failed: {result.stderr}")

#     def cleanup(self) -> None:
#         subprocess.run(["isolate", f"--box-id={self.box_id}", "--cleanup"], capture_output=True)

#     def run(self, cmd: List[str], env_vars: List[str] = []) -> Dict:
#         # Fayllar mavjudligini tekshirish
#         meta_file = "meta.txt"
        
#         isolate_cmd = [
#             "isolate", f"--box-id={self.box_id}", "--run",
#             "--processes=100",
#             "--time=30",
#             "--mem=1500000",
#             # MUHIM: Kataloglarni ulanishi (Mounting)
#             "--dir=/usr/bin",
#             "--dir=/usr/lib",
#             "--dir=/lib",
#             "--dir=/lib64",
#             "--dir=/etc",
#             "--dir=/usr/libexec",
#             "--dir=/usr/include",
#             "--dir=/usr/lib/jvm",
#             "--dir=/box=/box:rw", # /box papkasiga yozish ruxsati
#             "--env=PATH=/usr/bin:/usr/local/bin",
#             "--env=HOME=/tmp",
#             "--stdin=/dev/null", # Stdin xatolarini oldini olish uchun
#             f"--meta={meta_file}",
#             "--stdout=out.txt",
#             "--stderr=err.txt",
#             "--",
#         ]
#         isolate_cmd.extend(cmd)
        
#         result = subprocess.run(isolate_cmd, cwd=self.box, capture_output=True, text=True)

#         def read_box_file(name: str) -> str:
#             p = self.box / name
#             return p.read_text(errors="ignore").strip() if p.exists() else ""

#         return {
#             "stdout": read_box_file("out.txt"),
#             "stderr": read_box_file("err.txt"),
#             "exitcode": result.returncode,
#             "meta": read_box_file("meta.txt")
#         }

# def test_language(lang: str, code: str):
#     print(f"\n[+] Testing {lang.upper()}...")
#     iso = Isolate(box_id=1)
#     try:
#         iso.init()
#         # Kodni box ichiga yozamiz
#         file_path = iso.box / LANGUAGE_CONFIGS[lang]["file"]
#         file_path.write_text(code, encoding="utf-8")

#         config = LANGUAGE_CONFIGS[lang]
#         env = config.get("env", [])

#         # Kompilyatsiya
#         if config["compile"]:
#             res = iso.run(config["compile"], env_vars=env)
#             if res["exitcode"] != 0:
#                 print(f"FAIL: Compile Error\nSTDOUT: {res['stdout']}\nSTDERR: {res['stderr']}")
#                 return

#         # Ishga tushirish
#         res = iso.run(config["run"], env_vars=env)
#         if res["exitcode"] == 0:
#             print(f"SUCCESS: {res['stdout']}")
#         else:
#             print(f"RUNTIME ERROR:\nSTDOUT: {res['stdout']}\nSTDERR: {res['stderr']}")
#             print(f"META: {res.get('meta')}")

#     except Exception as e:
#         print(f"CRITICAL ERROR: {e}")
#     finally:
#         iso.cleanup()

# if __name__ == "__main__":
#     test_language("python", "print('Python OK')")
#     test_language("typescript", "const t: string = 'TS OK'; console.log(t);")
#     test_language("java", "public class Solution { public static void main(String[] args) { System.out.println(\"Java OK\"); } }")
#     test_language("go", "package main\nimport \"fmt\"\nfunc main() { fmt.Println(\"Go OK\") }")

import subprocess
from pathlib import Path
from typing import Dict, List, Optional
import os
import shutil

class Isolate:
    def __init__(self, box_id: int):
        self.box_id = box_id
        # Docker ichidagi bazaviy katalog
        self.base_path = Path(f"/var/local/lib/isolate/{box_id}")
        self.box_path = self.base_path / "box"

    def init(self) -> None:
        # 1. Avvalgi qoldiqlarni sudo bilan tozalash (Permission denied xatosini yo'qotadi)
        subprocess.run(["sudo", "isolate", f"--box-id={self.box_id}", "--cleanup"], capture_output=True)
        
        if self.base_path.exists():
            # Papkani o'chirish uchun ham sudo kerak bo'lishi mumkin
            subprocess.run(["sudo", "rm", "-rf", str(self.base_path)], capture_output=True)
        
        # 2. Yangidan yaratish
        result = subprocess.run(
            ["isolate", f"--box-id={self.box_id}", "--init"], 
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"Isolate init failed: {result.stderr}")
        
        # 3. Box papkasiga Python skriptingiz yozishi uchun ruxsat berish
        subprocess.run(["sudo", "chmod", "777", str(self.box_path)], capture_output=True)


    def cleanup(self) -> None:
        subprocess.run(["isolate", f"--box-id={self.box_id}", "--cleanup"], capture_output=True)

    def run(self, cmd: List[str]) -> Dict:
        isolate_cmd = [
            "isolate", f"--box-id={self.box_id}", "--run",
            "--processes=100", "--time=10", "--mem=1024000",
            "--dir=/usr/bin", "--dir=/usr/lib", "--dir=/lib", "--dir=/lib64",
            f"--stdout=out.txt", f"--stderr=err.txt", f"--meta=meta.txt",
            "--",
        ]
        isolate_cmd.extend(cmd)
        
        # Bajarish
        subprocess.run(isolate_cmd, cwd=self.box_path, capture_output=True)

        # MUHIM: Fayllarni o'qishdan oldin ruxsat berish (Permission Denied bo'lmasligi uchun)
        subprocess.run(["sudo", "chmod", "666", f"{self.box_path}/out.txt", f"{self.box_path}/err.txt", f"{self.box_path}/meta.txt"], capture_output=True)

        def read_box_file(name: str) -> str:
            p = self.box_path / name
            return p.read_text(errors="ignore").strip() if p.exists() else ""

        return {
            "stdout": read_box_file("out.txt"),
            "stderr": read_box_file("err.txt"),
            "exitcode": 0 # Bu yerda meta'dan exitcode'ni olish kerak aslida
        }


# =====================================================
# TILLARNI TEST QILISH FUNKSIYASI
# =====================================================
def test_language(lang: str, filename: str, code: str, run_cmd: List[str], compile_cmd: List[str] = None):
    print(f"\n[+] Testing {lang.upper()}...")
    iso = Isolate(box_id=1)
    
    try:
        iso.init()
        
        # Faylni faqat /box ichiga yozamiz
        target_file = iso.box_path / filename
        target_file.write_text(code, encoding="utf-8")
        
        # Kompilyatsiya
        if compile_cmd:
            res = iso.run(compile_cmd)
            if res["exitcode"] != 0:
                print(f"FAIL: Compile Error\nSTDOUT: {res['stdout']}\nSTDERR: {res['stderr']}")
                return

        # Ishga tushirish
        res = iso.run(run_cmd)
        if res["exitcode"] == 0:
            print(f"SUCCESS: {res['stdout']}")
        else:
            print(f"RUNTIME ERROR: {res['stderr']}\nSTDOUT: {res['stdout']}")
            
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
    finally:
        iso.cleanup()

# =====================================================
# ASOSIY QISM
# =====================================================
if __name__ == "__main__":
    # Python
    test_language("python", "solution.py", 
                  "print('Python OK')", 
                  ["/usr/bin/python3", "solution.py"])
    
    # C++
    test_language("cpp", "solution.cpp", 
                  "#include <iostream>\nint main() { std::cout << \"CPP OK\"; return 0; }", 
                  ["./solution"], ["/usr/bin/g++", "solution.cpp", "-o", "solution"])
    
    # TypeScript
    test_language("typescript", "solution.ts", 
                  "console.log('TS OK')", 
                  ["/usr/bin/node", "solution.js"], 
                  ["/usr/bin/node", "/usr/bin/tsc", "solution.ts", "--target", "ES2020"])

