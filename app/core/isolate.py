import subprocess
from pathlib import Path

# Til konfiguratsiyalari
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
        "compile": ["/usr/bin/gcc", "-O2", "-std=c11", "-o", "solution", "solution.c", "-lm"],
        "run": ["./solution"]
    },
    "java": {
        "file": "Solution.java",
        "compile": ["/usr/bin/javac", "Solution.java"],
        "run": ["/usr/bin/java", "Solution"]
    }
}


class Isolate:
    """Isolate sandbox manager"""
    
    def __init__(self, box_id: int):
        self.box_id = box_id
        self.base = Path(f"/var/local/lib/isolate/{box_id}")
        self.box = self.base / "box"

    def init(self):
        """Sandbox'ni initsializatsiya qilish"""
        try:
            subprocess.run(
                ["isolate", f"--box-id={self.box_id}", "--init"],
                check=True,
                capture_output=True,
                timeout=5
            )
        except subprocess.TimeoutExpired:
            raise Exception(f"Isolate init timeout for box {self.box_id}")
        except subprocess.CalledProcessError as e:
            raise Exception(f"Isolate init failed: {e.stderr.decode()}")

    def cleanup(self):
        """Sandbox'ni tozalash"""
        try:
            subprocess.run(
                ["isolate", f"--box-id={self.box_id}", "--cleanup"],
                capture_output=True,
                timeout=5
            )
        except:
            pass  # Cleanup xatolarini ignore qilamiz

    def run(self, cmd: list, stdin_data: str = "") -> dict:
        """
        Komandani sandbox ichida bajarish
        
        Args:
            cmd: Bajariladigan komanda
            stdin_data: STDIN uchun ma'lumotlar
        
        Returns:
            dict: stdout, stderr va meta ma'lumotlar
        """
        meta = self.box / "meta.txt"
        
        # Input faylini yozish (bo'sh bo'lsa ham)
        input_file = self.box / "input.txt"
        input_file.write_text(stdin_data if stdin_data else "", encoding="utf-8")
        
        # Isolate komandasi
        isolate_cmd = [
            "isolate",
            f"--box-id={self.box_id}",
            "--run",
            
            # ⏱ RESURS LIMITLARI
            "--time=2",             # CPU time limit (2 soniya)
            "--wall-time=5",        # Real time limit (5 soniya)
            "--mem=524288",         # 512MB xotira
            "--fsize=51200",        # 50MB fayl hajmi
            "--stack=262144",       # 256MB stack
            
            # 📁 I/O
            "--stdin=input.txt",
            "--stdout=out.txt",
            "--stderr=err.txt",
            f"--meta={meta}",
            
            # Bajarilishi kerak bo'lgan komanda
            "--",
        ] + cmd
        
        try:
            result = subprocess.run(
                isolate_cmd,
                cwd=self.base,
                timeout=10,  # Wall time + buffer
                check=False  # Exitcode'ni o'zimiz tekshiramiz
            )
            
            exitcode = result.returncode
            
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": "Wall Time Limit Exceeded (10s)",
                "meta": "status:TO\n",
                "exitcode": 1
            }
        
        # Output fayllarni o'qish
        stdout = ""
        stderr = ""
        meta_content = ""
        
        try:
            if (self.box / "out.txt").exists():
                stdout = (self.box / "out.txt").read_text(errors="ignore").strip()
        except:
            pass
        
        try:
            if (self.box / "err.txt").exists():
                stderr = (self.box / "err.txt").read_text(errors="ignore").strip()
        except:
            pass
        
        try:
            if meta.exists():
                meta_content = meta.read_text(errors="ignore")
                # DEBUG: Meta'ni log qilish
                print(f"[DEBUG] Box {self.box_id} meta:", meta_content[:200])
        except:
            pass
        
        return {
            "stdout": stdout,
            "stderr": stderr,
            "meta": meta_content,
            "exitcode": exitcode
        }