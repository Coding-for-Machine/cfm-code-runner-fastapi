import subprocess
from pathlib import Path
from typing import Dict, List, Optional


# ================== LANGUAGE CONFIGS ==================

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
        "compile": [
            "/usr/bin/tsc",
            "--target", "ES2020",
            "--module", "commonjs",
            "solution.ts"
        ],
        "run": ["/usr/bin/node", "solution.js"],
    },
    "go": {
        "file": "solution.go",
        "compile": ["/usr/bin/go", "build", "-o", "solution", "solution.go"],
        "run": ["./solution"],
    },
    "cpp": {
        "file": "solution.cpp",
        "compile": ["/usr/bin/g++", "-O2", "-std=c++17", "solution.cpp", "-o", "solution"],
        "run": ["./solution"],
    },
    "c": {
        "file": "solution.c",
        "compile": ["/usr/bin/gcc", "-O2", "-std=c11", "solution.c", "-lm", "-o", "solution"],
        "run": ["./solution"],
    },
    "java": {
        "file": "Solution.java",
        "compile": ["/usr/bin/javac", "Solution.java"],
        "run": ["/usr/bin/java", "Solution"],
    },
}


# ================== ISOLATE CLASS ==================

class Isolate:
    """
    Isolate sandbox wrapper
    """

    def __init__(self, box_id: int):
        self.box_id = box_id
        self.base = Path(f"/var/local/lib/isolate/{box_id}")
        self.box = self.base / "box"

    # ---------- INIT ----------

    def init(self) -> None:
        try:
            subprocess.run(
                ["isolate", f"--box-id={self.box_id}", "--init"],
                check=True,
                capture_output=True,
                timeout=5,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Isolate init timeout (box {self.box_id})")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Isolate init failed: {e.stderr.decode(errors='ignore')}"
            )

    # ---------- CLEANUP ----------

    def cleanup(self) -> None:
        try:
            subprocess.run(
                ["isolate", f"--box-id={self.box_id}", "--cleanup"],
                timeout=5,
                capture_output=True,
            )
        except Exception:
            pass  # cleanup xatolari ignore qilinadi

    # ---------- RUN COMMAND ----------

    def run(self, cmd: List[str], stdin_data: Optional[str] = None) -> Dict:
        """
        Sandbox ichida komanda bajarish
        """

        # Fayllar faqat box/ ichida bo'lishi shart
        meta_file = self.box / "meta.txt"
        input_file = self.box / "input.txt"

        if stdin_data:
            input_file.write_text(stdin_data, encoding="utf-8")

        isolate_cmd = [
            "isolate",
            f"--box-id={self.box_id}",
            "--run",

            # ===== LIMITLAR =====
            "--time=2",
            "--wall-time=5",
            "--mem=524288",     # 512MB
            "--fsize=51200",    # 50MB
            "--stack=262144",   # 256MB

            # ===== I/O =====
            "--stdout=out.txt",
            "--stderr=err.txt",
            "--meta=meta.txt",
        ]

        if stdin_data:
            isolate_cmd.append("--stdin=input.txt")

        isolate_cmd.append("--")
        isolate_cmd.extend(cmd)   # 🔥 MUHIM

        try:
            result = subprocess.run(
                isolate_cmd,
                cwd=self.box,     # 🔥 MUHIM
                timeout=10,
                check=False,
            )
            exitcode = result.returncode

        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": "Wall Time Limit Exceeded",
                "meta": "status:TO\n",
                "exitcode": 1,
            }

        # ---------- OUTPUT O'QISH ----------

        def read_file(path: Path) -> str:
            try:
                if path.exists():
                    return path.read_text(errors="ignore").strip()
            except Exception:
                pass
            return ""

        stdout = read_file(self.box / "out.txt")
        stderr = read_file(self.box / "err.txt")
        meta = read_file(meta_file)

        return {
            "stdout": stdout,
            "stderr": stderr,
            "meta": meta,
            "exitcode": exitcode,
        }
