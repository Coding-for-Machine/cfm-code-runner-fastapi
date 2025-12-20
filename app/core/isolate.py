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
        "run": ["/usr/local/bin/python3", "solution.py"],
    },
    "javascript": {
        "file": "solution.js",
        "compile": None,
        "run": ["/opt/nodejs/bin/node", "solution.js"],
    },
    "typescript": {
        "file": "solution.ts",
        # TSC ni to'g'ridan-to'g'ri emas, NODE orqali chaqiramiz (Symbolic link xatosini yopadi)
        "compile": ["/opt/nodejs/bin/node", "/opt/nodejs/bin/tsc", "solution.ts", "--target", "ES2020", "--module", "CommonJS"],
        "run": ["/opt/nodejs/bin/node", "solution.js"],
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
    "java": {
        "file": "Solution.java",
        "compile": ["/usr/bin/javac", "-J-Xms128M", "-J-Xmx512M", "Solution.java"],
        "run": ["/usr/bin/java", "-Xmx512M", "Solution"],
    },
}

# =====================================================
# ISOLATE SANDBOX
# =====================================================
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

    def run(self, cmd: List[str], env_vars: List[str] = []) -> Dict:
        meta_file = self.box / "meta.txt"
        stdout_file = self.box / "out.txt"
        stderr_file = self.box / "err.txt"

        isolate_cmd = [
            "isolate",
            f"--box-id={self.box_id}",
            "--run",
            "--processes=100",
            "--time=30",
            "--mem=2048000",       # Xotira 2GB ga oshirildi (Java uchun)
            "--dir=/usr/bin",
            "--dir=/usr/lib",
            "--dir=/lib",
            "--dir=/lib64",
            "--dir=/usr/local/bin",
            "--dir=/opt/nodejs",
            "--dir=/usr/libexec",
            "--dir=/usr/include",
            "--dir=/usr/lib/jvm",   # Java uchun
            "--dir=/etc",
            "--env=PATH=/usr/bin:/usr/local/bin:/opt/nodejs/bin",
            "--env=HOME=/tmp",
            "--stdout=out.txt",
            "--stderr=err.txt",
            "--meta=meta.txt",
        ]
        
        for env in env_vars:
            isolate_cmd.append(f"--env={env}")
            
        isolate_cmd.extend(["--", *cmd])
        
        # Capture_output=True qilib barcha xatoni ko'ramiz
        result = subprocess.run(isolate_cmd, cwd=self.box, capture_output=True, text=True)

        def read_file(path: Path) -> str:
            return path.read_text(errors="ignore").strip() if path.exists() else ""

        return {
            "stdout": read_file(stdout_file),
            "stderr": read_file(stderr_file),
            "exitcode": result.returncode,
        }

# =========================
# TEST FUNKSIYASI
# =========================
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

# =========================
# TESTLAR
# =========================
if __name__ == "__main__":
    # TypeScript
    test_language("typescript", "const a: number = 10; const b: number = 20; console.log(`TS Result: ${a + b}`);")
    
    # Java
    test_language("java", "public class Solution { public static void main(String[] args) { System.out.println(\"Java is Working!\"); } }")
    
    # Python (tekshiruv)
    test_language("python", "print('Python is Working!')")

    # Java testi
    test_language("java", "public class Solution { public static void main(String[] args) { System.out.println(\"Java OK!\"); } }")
    
    # TypeScript testi
    test_language("typescript", "const msg: string = 'TypeScript OK!'; console.log(msg);")
    
    # Python testi (tekshiruv uchun)
    test_language("python", "print('Python OK!')")

    test_language("cpp", "#include <iostream>\nint main() { std::cout << \"Hello from C++\"; return 0; }")
    
    test_language("python", "print('Hello from Python')")
    
    test_language("javascript", "console.log('Hello from Node.js');")
    
    test_language("go", "package main\nimport \"fmt\"\nfunc main() { fmt.Println(\"Hello from Go\") }")
    
    test_language("java", "public class Solution { public static void main(String[] args) { System.out.println(\"Hello from Java\"); } }")
