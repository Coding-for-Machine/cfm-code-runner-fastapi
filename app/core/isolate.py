import subprocess
from pathlib import Path
from typing import Dict, List, Optional

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
        "compile": ["/usr/bin/node", "/usr/bin/tsc", "solution.ts", "--target", "ES2020", "--module", "CommonJS"],
        "run": ["/usr/bin/node", "solution.js"],
    },
    "go": {
        "file": "solution.go",
        "compile": ["/usr/bin/go", "build", "-o", "solution", "solution.go"],
        "run": ["./solution"],
        "env": ["GOCACHE=/tmp", "HOME=/tmp"]
    },
    "cpp": {
        "file": "solution.cpp",
        "compile": ["/usr/bin/g++", "-O2", "solution.cpp", "-o", "solution"],
        "run": ["./solution"],
    },
}

class Isolate:
    def __init__(self, box_id: int):
        self.box_id = box_id
        self.base = Path(f"/var/local/lib/isolate/{box_id}")
        self.box = self.base / "box"

    def init(self) -> None:
        subprocess.run(["isolate", f"--box-id={self.box_id}", "--cleanup"], capture_output=True)
        subprocess.run(["isolate", f"--box-id={self.box_id}", "--init"], check=True, capture_output=True)

    def cleanup(self) -> None:
        subprocess.run(["isolate", f"--box-id={self.box_id}", "--cleanup"], capture_output=True)

    def run(self, cmd: List[str], stdin_data: Optional[str] = "", env_vars: List[str] = []) -> Dict:
        meta_file = self.box / "meta.txt"
        stdout_file = self.box / "out.txt"
        stderr_file = self.box / "err.txt"
        
        # INPUTNI YOZISH
        (self.box / "input.txt").write_text(stdin_data or "", encoding="utf-8")

        # DIQQAT: Bu yerda oxiridagi vergulni olib tashladik
        isolate_cmd = [
            "isolate",
            f"--box-id={self.box_id}",
            "--run",
            "--processes=100",
            "--time=15",
            "--mem=512000",
            "--dir=/usr/bin",
            "--dir=/usr/lib",
            "--dir=/lib",
            "--dir=/lib64",
            "--dir=/etc",
            "--dir=/usr/local/lib",
            "--stdin=input.txt",
            "--stdout=out.txt",
            "--stderr=err.txt",
            f"--meta={meta_file}",
        ]
        
        # Env o'zgaruvchilarni qo'shish
        for env in env_vars:
            isolate_cmd.append(f"--env={env}")
            
        # Buyruqni (cmd) oxiriga qo'shish
        isolate_cmd.append("--")
        isolate_cmd.extend(cmd)
        
        # Subprocessni yurgizish
        result = subprocess.run(isolate_cmd, cwd=self.box, capture_output=True, text=True)

        def read_file(path: Path) -> str:
            return path.read_text(errors="ignore").strip() if path.exists() else ""

        return {
            "stdout": read_file(stdout_file),
            "stderr": read_file(stderr_file),
            "meta": read_file(meta_file),
            "exitcode": result.returncode,
        }

def test_language(lang: str, code: str):
    print(f"\n[+] Testing {lang.upper()}...")
    iso = Isolate(box_id=1)
    iso.init()
    
    file_path = iso.box / LANGUAGE_CONFIGS[lang]["file"]
    file_path.write_text(code, encoding="utf-8")

    config = LANGUAGE_CONFIGS[lang]
    extra_env = config.get("env", [])

    # Kompilyatsiya
    if config["compile"]:
        res = iso.run(config["compile"], env_vars=extra_env)
        if res["exitcode"] != 0:
            print(f"FAIL: Compile Error\nSTDERR: {res['stderr']}")
            return

    # Ishga tushirish
    res = iso.run(config["run"], env_vars=extra_env)
    if res["exitcode"] == 0:
        print(f"RESULT: {res['stdout']}")
    else:
        print(f"RUNTIME ERROR: {res['stderr']}")
    
    iso.cleanup()

if __name__ == "__main__":
    # TypeScript
    test_language("typescript", "const a: number = 10; const b: number = 20; console.log(`TS Result: ${a + b}`);")
    
    # Python (tekshiruv)
    test_language("python", "print('Python is Working!')")

    test_language("cpp", "#include <iostream>\nint main() { std::cout << \"Hello from C++\"; return 0; }")
    
    test_language("python", "print('Hello from Python')")
    
    test_language("javascript", "console.log('Hello from Node.js');")

    # TypeScript testi qo'shildi
    test_language("typescript", "const t: string = 'Hello from TS'; console.log(t);")
    
    test_language("go", "package main\nimport \"fmt\"\nfunc main() { fmt.Println(\"Hello from Go\") }")
