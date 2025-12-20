import subprocess
from pathlib import Path
from typing import Dict, List, Optional
import os
import shutil

class Isolate:
    def __init__(self, box_id: int):
        self.box_id = box_id
        # Docker ichidagi standart yo'l
        self.base_path = Path(f"/var/local/lib/isolate/{box_id}")
        self.box_path = self.base_path / "box"

    def init(self) -> None:
        # Dockerda sudo ishlatilmaydi, chunki biz rootmiz
        subprocess.run(["isolate", f"--box-id={self.box_id}", "--cleanup"], capture_output=True)
        
        if self.base_path.exists():
            shutil.rmtree(self.base_path)
        
        result = subprocess.run(
            ["isolate", f"--box-id={self.box_id}", "--init"], 
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"Isolate init failed: {result.stderr}")
        
        # Box papkasiga hamma yoza olishi uchun (Permission xatosini oldini oladi)
        os.chmod(self.box_path, 0o777)

    def cleanup(self) -> None:
        subprocess.run(["isolate", f"--box-id={self.box_id}", "--cleanup"], capture_output=True)

    def run(self, cmd: List[str]) -> Dict:
        # Isolate buyrug'i
        isolate_cmd = [
            "isolate", f"--box-id={self.box_id}", "--run",
            "--processes=100",
            "--time=10",
            "--mem=1024000",
            "--dir=/usr/bin",
            "--dir=/usr/lib",
            "--dir=/lib",
            "--dir=/lib64",
            "--env=PATH=/usr/bin:/bin",
            f"--meta={self.box_path}/meta.txt",
            f"--stdout={self.box_path}/out.txt",
            f"--stderr={self.box_path}/err.txt",
            "--",
        ]
        isolate_cmd.extend(cmd)
        
        # Bajarish
        subprocess.run(isolate_cmd, capture_output=True)

        # Ruxsatni o'zgartirishga harakat qilamiz, agar xato bersa (Operation not permitted), 
        # Python'ning o'zi orqali o'qishga o'tamiz
        for f in ["out.txt", "err.txt", "meta.txt"]:
            file_p = self.box_path / f
            try:
                if file_p.exists():
                    os.chmod(file_p, 0o666)
            except OSError:
                # Agar chmod ruxsat bermasa, sudo orqali ruxsatni ochishga urinib ko'ramiz
                subprocess.run(["sudo", "chmod", "666", str(file_p)], capture_output=True)

        def read_box_file(name: str) -> str:
            p = self.box_path / name
            try:
                # Agar oddiy o'qish ishlamasa, sudo cat orqali o'qiymiz
                if p.exists():
                    return p.read_text(errors="ignore").strip()
            except PermissionError:
                res = subprocess.run(["sudo", "cat", str(p)], capture_output=True, text=True)
                return res.stdout.strip()
            return ""

        return {
            "stdout": read_box_file("out.txt"),
            "stderr": read_box_file("err.txt"),
            "exitcode": 0
        }

def test_language(lang: str, filename: str, code: str, run_cmd: List[str], compile_cmd: List[str] = None):
    print(f"\n[+] Testing {lang.upper()}...")
    iso = Isolate(box_id=1)
    try:
        iso.init()
        (iso.box_path / filename).write_text(code, encoding="utf-8")
        
        if compile_cmd:
            res = iso.run(compile_cmd)
            if not res["stdout"] and res["stderr"]: # Agar kompilyatsiya xatosi bo'lsa
                print(f"FAIL: Compile Error\n{res['stderr']}")
                return

        res = iso.run(run_cmd)
        if res["stdout"]:
            print(f"SUCCESS: {res['stdout']}")
        else:
            print(f"ERROR/EMPTY: {res['stderr']}")
            
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
    finally:
        iso.cleanup()

if __name__ == "__main__":
    test_language("python", "solution.py", "print('Python OK')", ["/usr/bin/python3", "solution.py"])
    test_language("cpp", "solution.cpp", "#include <iostream>\nint main() { std::cout << \"CPP OK\"; return 0; }", ["./solution"], ["/usr/bin/g++", "solution.cpp", "-o", "solution"])
