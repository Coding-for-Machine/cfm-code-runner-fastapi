import subprocess
from pathlib import Path
from typing import Dict, List, Optional
import os

# =====================================================
# TILLAR SOZLAMALARI (Docker yo'llari bilan)
# =====================================================
LANGUAGE_CONFIGS: Dict[str, Dict] = {
    "python": {
        "file": "solution.py",
        "compile": None,
        "run": ["/usr/bin/python3", "solution.py"],
    },
    "javascript": {
        "file": "solution.js",
        "compile": None,
        "run": ["/usr/bin/node", "solution.js"],
    },
    "typescript": {
        "file": "solution.ts",
        # TSC ni Node orqali chaqirish xavfsizroq
        "compile": ["/usr/bin/node", "/usr/bin/tsc", "solution.ts", "--target", "ES2020", "--module", "CommonJS"],
        "run": ["/usr/bin/node", "solution.js"],
    },
    "go": {
        "file": "solution.go",
        "compile": ["/usr/local/go/bin/go", "build", "-o", "solution", "solution.go"],
        "run": ["./solution"],
        "env": ["GOCACHE=/tmp", "HOME=/tmp"]
    },
    "cpp": {
        "file": "solution.cpp",
        "compile": ["/usr/bin/g++", "-O2", "solution.cpp", "-o", "solution"],
        "run": ["./solution"],
    },
    "java": {
        "file": "Solution.java",
        "compile": ["/usr/bin/javac", "-J-Xms128M", "-J-Xmx512M", "Solution.java"],
        "run": ["/usr/bin/java", "-Xmx512M", "Solution"],
    },
}

class Isolate:
    def __init__(self, box_id: int):
        self.box_id = box_id
        self.base = Path(f"/var/local/lib/isolate/{box_id}")
        self.box = self.base / "box"

    def init(self) -> None:
        # 1. Avval hammasini tozalash (majburiy)
        subprocess.run(["isolate", f"--box-id={self.box_id}", "--cleanup"], capture_output=True)
        
        # 2. Agar papka ichida begona fayllar qolib ketgan bo'lsa, ularni o'chirish
        if os.path.exists(self.base):
            import shutil
            shutil.rmtree(self.base)
        
        # 3. Endi init qilish
        result = subprocess.run(
            ["isolate", f"--box-id={self.box_id}", "--init"], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode != 0:
            print(f"DEBUG: Isolate init failed. Stderr: {result.stderr}")
            raise RuntimeError(f"Isolate init failed: {result.stderr}")


    def cleanup(self) -> None:
        subprocess.run(["isolate", f"--box-id={self.box_id}", "--cleanup"], capture_output=True)

    def run(self, cmd: List[str], env_vars: List[str] = []) -> Dict:
        meta_file = self.box / "meta.txt"
        stdout_file = self.box / "out.txt"
        stderr_file = self.box / "err.txt"

        isolate_cmd = [
            "isolate", f"--box-id={self.box_id}", "--run",
            "--processes=100",
            "--time=30",
            "--mem=1500000",
            "--dir=/usr/bin",
            "--dir=/usr/lib",
            "--dir=/lib",
            "--dir=/lib64",
            "--dir=/usr/local/go", # Go uchun
            "--dir=/usr/libexec",  # C++ linker uchun
            "--dir=/usr/lib/jvm",  # Java uchun
            "--dir=/etc",
            "--env=PATH=/usr/bin:/usr/local/bin:/usr/local/go/bin",
            "--env=HOME=/tmp",
            "--stdout=out.txt", "--stderr=err.txt", "--meta=meta.txt",
        ]
        
        for env in env_vars:
            isolate_cmd.append(f"--env={env}")
            
        isolate_cmd.extend(["--", *cmd])
        
        # Konteyner ichida Isolate-ni yurgizish
        result = subprocess.run(isolate_cmd, cwd=self.box, capture_output=True, text=True)

        def read_file(path: Path) -> str:
            return path.read_text(errors="ignore").strip() if path.exists() else ""

        return {
            "stdout": read_file(stdout_file),
            "stderr": read_file(stderr_file),
            "exitcode": result.returncode,
        }

def test_language(lang: str, code: str):
    print(f"\n[+] Testing {lang.upper()}...")
    iso = Isolate(box_id=1)
    try:
        iso.init()
        file_path = iso.box / LANGUAGE_CONFIGS[lang]["file"]
        file_path.write_text(code, encoding="utf-8")

        config = LANGUAGE_CONFIGS[lang]
        if config["compile"]:
            res = iso.run(config["compile"], env_vars=config.get("env", []))
            if res["exitcode"] != 0:
                print(f"FAIL: Compile Error\n{res['stderr']}")
                return

        res = iso.run(config["run"], env_vars=config.get("env", []))
        if res["exitcode"] == 0:
            print(f"SUCCESS: {res['stdout']}")
        else:
            print(f"RUNTIME ERROR: {res['stderr']}")
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
    finally:
        iso.cleanup()

if __name__ == "__main__":
    test_language("python", "print('Python OK')")
    test_language("typescript", "const t: string = 'TS OK'; console.log(t);")
    test_language("java", "public class Solution { public static void main(String[] args) { System.out.println(\"Java OK\"); } }")
    test_language("go", "package main\nimport \"fmt\"\nfunc main() { fmt.Println(\"Go OK\") }")
