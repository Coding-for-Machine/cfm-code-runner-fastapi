import subprocess
from pathlib import Path
from typing import Dict, List, Optional


# =====================================================
# LANGUAGE CONFIGURATIONS
# =====================================================
LANGUAGE_CONFIGS: Dict[str, Dict] = {
    "python": {
        "file": "solution.py",
        "compile": None,
        "run": ["/usr/bin/python3", "solution.py"],
    },
    "c": {
        "file": "solution.c",
        "compile": ["/usr/bin/gcc", "-O2", "-std=c11", "solution.c", "-lm", "-o", "solution"],
        "run": ["./solution"],
    },
    "cpp": {
        "file": "solution.cpp",
        "compile": ["/usr/bin/g++", "-O2", "-std=c++17", "solution.cpp", "-o", "solution"],
        "run": ["./solution"],
    },
    "java": {
        "file": "Solution.java",
        "compile": ["/usr/bin/javac", "Solution.java"],
        "run": ["/usr/bin/java", "Solution"],
    },
    "go": {
        "file": "solution.go",
        "compile": ["/usr/bin/go", "build", "-o", "solution", "solution.go"],
        "run": ["./solution"],
    },
    "javascript": {
        "file": "solution.js",
        "compile": None,
        "run": ["/usr/bin/node", "solution.js"],
    },
    "typescript": {
        "file": "solution.ts",
        "compile": ["/usr/bin/tsc", "--target", "ES2020", "--module", "commonjs", "solution.ts"],
        "run": ["/usr/bin/node", "solution.js"],
    },
}


class Isolate:
    """
    Isolate sandbox wrapper with proper cleanup
    
    MUHIM:
        - Init qilishdan oldin cleanup qilish
        - Har doim to'liq yo'llardan foydalanish
        - Meta fayl BASE ichida yaratiladi
    """
    
    def __init__(self, box_id: int):
        self.box_id = box_id
        self.base = Path(f"/var/local/lib/isolate/{box_id}")
        self.box = self.base / "box"

    def init(self) -> None:
        """
        Sandbox'ni initsializatsiya qilish
        
        MUHIM: To'liq cleanup va sync qilish
        """
        # 1. Isolate cleanup
        try:
            subprocess.run(
                ["isolate", f"--box-id={self.box_id}", "--cleanup"],
                timeout=5,
                capture_output=True,
            )
        except Exception:
            pass
        
        # 2. To'liq directory o'chirish
        if self.base.exists():
            try:
                import shutil
                shutil.rmtree(self.base, ignore_errors=True)
            except Exception:
                pass
        
        # 3. Filesystem sync (Docker uchun MUHIM!)
        try:
            subprocess.run(["sync"], timeout=1, capture_output=True)
        except Exception:
            pass
        
        # 4. Biroz kutish
        import time
        time.sleep(0.1)
        
        # 5. Init qilish
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = subprocess.run(
                    ["isolate", f"--box-id={self.box_id}", "--init"],
                    check=True,
                    capture_output=True,
                    timeout=5,
                )
                
                # 6. Box bo'sh ekanligini tekshirish
                if self.box.exists():
                    box_contents = list(self.box.iterdir())
                    if box_contents:
                        # Box bo'sh emas - tozalash
                        for item in box_contents:
                            try:
                                if item.is_file():
                                    item.unlink()
                                elif item.is_dir():
                                    import shutil
                                    shutil.rmtree(item)
                            except Exception:
                                pass
                
                return  # Success!
                
            except subprocess.TimeoutExpired:
                if attempt == max_retries - 1:
                    raise RuntimeError(f"Isolate init timeout after {max_retries} attempts")
                time.sleep(0.2)
                
            except subprocess.CalledProcessError as e:
                stderr = e.stderr.decode(errors='ignore')
                
                if "Unexpected mountpoint" in stderr and attempt < max_retries - 1:
                    # Retry with full cleanup
                    try:
                        subprocess.run(["isolate", f"--box-id={self.box_id}", "--cleanup"], 
                                     timeout=5, capture_output=True)
                    except Exception:
                        pass
                    
                    if self.base.exists():
                        import shutil
                        shutil.rmtree(self.base, ignore_errors=True)
                    
                    time.sleep(0.2)
                    continue
                else:
                    raise RuntimeError(f"Isolate init failed: {stderr}")

    def cleanup(self) -> None:
        """
        Sandbox'ni tozalash
        
        Har doim chaqiriladi, xatolar ignore qilinadi
        """
        try:
            subprocess.run(
                ["isolate", f"--box-id={self.box_id}", "--cleanup"],
                timeout=5,
                capture_output=True,
            )
        except Exception:
            pass
        
        # Qo'shimcha: fayllarni to'g'ridan-to'g'ri o'chirish
        try:
            if self.base.exists():
                import shutil
                shutil.rmtree(self.base)
        except Exception:
            pass

    def run(self, cmd: List[str], stdin_data: Optional[str] = "") -> Dict:
        """
        Komandani sandbox ichida bajarish
        
        MUHIM:
            - Meta fayl to'liq yo'l bilan beriladi
            - CWD base directoriyda
            - Barcha I/O fayllar box ichida
        """
        # Fayl yo'llari (to'liq yo'llar)
        input_file = self.box / "input.txt"
        stdout_file = self.box / "out.txt"
        stderr_file = self.box / "err.txt"
        meta_file = self.base / "meta.txt"

        # STDIN yozish
        try:
            input_file.write_text(stdin_data or "", encoding="utf-8")
        except Exception as e:
            return {
                "stdout": "",
                "stderr": f"Failed to write input: {str(e)}",
                "meta": "status:XX\n",
                "exitcode": 1,
            }

        # Isolate komandasi
        isolate_cmd = [
            "isolate",
            f"--box-id={self.box_id}",
            "--run",
            
            # Limits
            "--time=2",
            "--wall-time=5",
            "--mem=524288",
            "--fsize=51200",
            "--stack=262144",
            
            # I/O (faqat nisbiy yo'llar box ichida)
            "--stdin=input.txt",
            "--stdout=out.txt",
            "--stderr=err.txt",
            f"--meta={meta_file}",  # To'liq yo'l!
            
            "--",
        ]
        isolate_cmd.extend(cmd)

        try:
            result = subprocess.run(
                isolate_cmd,
                cwd=self.base,  # Base directoriyda
                timeout=10,
                check=False,
            )
            exitcode = result.returncode

        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": "Wall Time Limit Exceeded (10s)",
                "meta": "status:TO\ntime:10.0\n",
                "exitcode": 1,
            }

        # Output o'qish
        def read_file(path: Path) -> str:
            try:
                if path.exists():
                    return path.read_text(errors="ignore").strip()
            except Exception:
                pass
            return ""

        return {
            "stdout": read_file(stdout_file),
            "stderr": read_file(stderr_file),
            "meta": read_file(meta_file),
            "exitcode": exitcode,
        }