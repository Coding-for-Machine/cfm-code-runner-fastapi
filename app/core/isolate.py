import subprocess
from pathlib import Path

LANGUAGE_CONFIGS = {
    "python": {
        "file": "solution.py",
        "compile": None,
        "run": ["/usr/bin/python3", "solution.py"]
    },
    "javascript": {
        "file": "solution.js",
        "compile": None,
        "run": ["/usr/bin/node", "solution.js"]
    },
    "typescript": {
        "file": "solution.ts",
        "compile": ["/usr/bin/tsc", "--target", "ES2020", "--module", "commonjs", "solution.ts"],
        "run": ["/usr/bin/node", "solution.js"]
    },
    "go": {
        "file": "solution.go",
        "compile": ["/usr/bin/go", "build", "-o", "solution", "solution.go"],
        "run": ["./solution"]
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
            pass  # Cleanup xatolarini ignore qilamiz

    def run(self, cmd: list, stdin_data: str = "") -> dict:
        meta = self.box / "meta.txt"
        
        # Input faylini yozish
        if stdin_data:
            (self.box / "input.txt").write_text(stdin_data, encoding="utf-8")
        else:
            # Bo'sh input fayl yaratish (stdin kutayotgan dasturlar uchun)
            (self.box / "input.txt").write_text("", encoding="utf-8")
        
        isolate_cmd = [
            "isolate",
            f"--box-id={self.box_id}",
            "--run",
            
            # 🔐 XAVFSIZLIK
            "--processes=1",
            "--no-network",
            
            # ⏱ LIMITLAR
            "--time=2",           # CPU time limit
            "--wall-time=3",      # Real time limit
            "--mem=262144",       # 256MB
            "--fsize=10240",      # 10MB file size
            "--stack=8192",       # 8MB stack
            
            "--stdin=input.txt",
            "--stdout=out.txt",
            "--stderr=err.txt",
            f"--meta={meta}",
            
            "--",
        ] + cmd
        
        try:
            subprocess.run(
                isolate_cmd,
                cwd=self.base,
                timeout=5,
                check=False
            )
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": "Wall Time Limit Exceeded",
                "meta": "status:TO\n"
            }
        
        return {
            "stdout": (self.box / "out.txt").read_text(errors="ignore").strip() if (self.box / "out.txt").exists() else "",
            "stderr": (self.box / "err.txt").read_text(errors="ignore").strip() if (self.box / "err.txt").exists() else "",
            "meta": meta.read_text(errors="ignore") if meta.exists() else ""
        }