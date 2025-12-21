import subprocess
from pathlib import Path
from typing import Dict, List, Optional
import shutil

class Isolate:
    def __init__(self, box_id: int):
        self.box_id = box_id
        self.base_path = Path(f"/var/local/lib/isolate/{box_id}")
        self.box_path = self.base_path / "box"

    def init(self) -> None:
        """Isolate sandbox'ni initsializatsiya qilish"""
        # Tozalash
        subprocess.run(
            ["isolate", f"--box-id={self.box_id}", "--cleanup"], 
            capture_output=True
        )
        
        # Yangidan yaratish
        result = subprocess.run(
            ["isolate", f"--box-id={self.box_id}", "--init"], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Isolate init xato: {result.stderr}")
        
        # Box papkasini yaratish (agar mavjud bo'lmasa)
        self.box_path.mkdir(parents=True, exist_ok=True)

    def cleanup(self) -> None:
        """Sandbox'ni tozalash"""
        subprocess.run(
            ["isolate", f"--box-id={self.box_id}", "--cleanup"],
            capture_output=True
        )

    def run(self, cmd: List[str], stdin_data: str = "", env_vars: Dict[str, str] = None) -> Dict:
        """Dasturni isolate ichida ishga tushirish"""
        
        # Stdout/stderr fayllarini oldindan tozalash
        for fname in ["out.txt", "err.txt", "meta.txt"]:
            fpath = self.box_path / fname
            if fpath.exists():
                fpath.unlink()
        
        # MUHIM: Meta fayl HOST tizimida bo'lishi kerak
        meta_file = self.box_path / "meta.txt"
        
        # Isolate buyrug'i
        isolate_cmd = [
            "isolate",
            f"--box-id={self.box_id}",
            "--run",
            # Resurs cheklovlari
            "--processes=50",
            "--wall-time=30",
            "--time=10",
            "--extra-time=5",
            "--mem=1048576",  # 1GB - Go uchun
            "--stack=524288",  # 512MB
            # Kataloglarni ulash (exec ruxsati bilan!)
            "--dir=/usr/bin",
            "--dir=/usr/lib",
            "--dir=/lib",
            "--dir=/lib64",
            "--dir=/etc",
            # Java uchun zarur
            "--dir=/usr/lib/jvm",
            "--dir=/usr/libexec",
            # Share va locale
            "--dir=/usr/share:maybe",
            # Environment variables
            "--env=PATH=/usr/bin:/usr/local/bin",
            "--env=HOME=/tmp",
            "--env=TMPDIR=/tmp",
        ]
        
        # Qo'shimcha environment variables
        if env_vars:
            for key, value in env_vars.items():
                isolate_cmd.append(f"--env={key}={value}")
        
        # Meta fayl (HOST yo'li!)
        isolate_cmd.append(f"--meta={meta_file}")
        
        # Stdout va stderr (isolate ichidagi yo'l)
        isolate_cmd.extend([
            "--stdout=out.txt",
            "--stderr=err.txt",
        ])
        
        # Stdin (agar kerak bo'lsa)
        if stdin_data:
            stdin_file = self.box_path / "input.txt"
            stdin_file.write_text(stdin_data, encoding="utf-8")
            isolate_cmd.append("--stdin=input.txt")
        
        # Buyruq
        isolate_cmd.append("--")
        isolate_cmd.extend(cmd)
        
        # Ishga tushirish
        result = subprocess.run(
            isolate_cmd,
            capture_output=True,
            text=True
        )
        
        # Natijalarni o'qish
        def read_file(name: str) -> str:
            fpath = self.box_path / name
            if fpath.exists():
                try:
                    return fpath.read_text(encoding="utf-8", errors="ignore").strip()
                except:
                    return ""
            return ""
        
        return {
            "stdout": read_file("out.txt"),
            "stderr": read_file("err.txt"),
            "exitcode": result.returncode,
            "meta": read_file("meta.txt"),
            "isolate_stderr": result.stderr
        }


# =====================================================
# TIL KONFIGURATSIYALARI
# =====================================================
LANGUAGES = {
    "python": {
        "file": "solution.py",
        "compile": None,
        "run": ["/usr/bin/python3", "solution.py"],
    },
    "javascript": {
        "file": "solution.js",
        "compile": None,
        "run": ["/usr/bin/nodejs", "solution.js"],  # node o'rniga nodejs
    },
    "typescript": {
        "file": "solution.ts",
        "compile": [
            "/usr/bin/nodejs", "/usr/bin/tsc",  # node o'rniga nodejs
            "solution.ts",
            "--outDir", ".",
            "--target", "ES2020",
            "--module", "CommonJS"
        ],
        "run": ["/usr/bin/nodejs", "solution.js"],  # node o'rniga nodejs
    },
    "cpp": {
        "file": "solution.cpp",
        "compile": [
            "/usr/bin/g++",
            "-O2",
            "-std=c++17",
            "solution.cpp",
            "-o", "solution"
        ],
        "run": ["./solution"],
    },
    "java": {
        "file": "Solution.java",
        "compile": [
            "/usr/bin/javac",
            "-J-Xms64M",
            "-J-Xmx256M",
            "Solution.java"
        ],
        "run": [
            "/usr/bin/java",
            "-Xms64M",
            "-Xmx256M",
            "Solution"
        ],
    },
    "go": {
        "file": "solution.go",
        "compile": [
            "/usr/bin/go", "build",
            "-o", "solution",
            "solution.go"
        ],
        "run": ["./solution"],
        "env": {
            "GOCACHE": "/tmp/gocache",
            "GOPATH": "/tmp/go",
        }
    },
}


def test_language(lang: str, code: str, stdin_data: str = ""):
    """Tilni test qilish"""
    print(f"\n{'='*50}")
    print(f"Testing {lang.upper()}")
    print('='*50)
    
    if lang not in LANGUAGES:
        print(f"ERROR: Til '{lang}' topilmadi!")
        return
    
    config = LANGUAGES[lang]
    iso = Isolate(box_id=1)
    
    try:
        # Initsializatsiya
        iso.init()
        print(f"✓ Sandbox yaratildi: {iso.box_path}")
        
        # Kodni yozish
        code_file = iso.box_path / config["file"]
        code_file.write_text(code, encoding="utf-8")
        print(f"✓ Kod yozildi: {code_file}")
        
        # Kompilyatsiya (agar kerak bo'lsa)
        if config["compile"]:
            print("📦 Kompilyatsiya...")
            env = config.get("env", {})
            res = iso.run(config["compile"], env_vars=env)
            
            if res["exitcode"] != 0:
                print(f"❌ KOMPILYATSIYA XATOSI:")
                print(f"Exit code: {res['exitcode']}")
                print(f"STDOUT: {res['stdout']}")
                print(f"STDERR: {res['stderr']}")
                print(f"Isolate stderr: {res['isolate_stderr']}")
                print(f"META: {res['meta']}")
                return
            print("✓ Kompilyatsiya muvaffaqiyatli")
        
        # Ishga tushirish
        print("▶ Ishga tushirilmoqda...")
        env = config.get("env", {})
        res = iso.run(config["run"], stdin_data=stdin_data, env_vars=env)
        
        # Natija
        print(f"\n📊 Natija:")
        print(f"Exit code: {res['exitcode']}")
        
        if res["exitcode"] == 0:
            print(f"✅ SUCCESS!")
            print(f"Output: {res['stdout']}")
        else:
            print(f"❌ RUNTIME ERROR!")
            print(f"STDOUT: {res['stdout']}")
            print(f"STDERR: {res['stderr']}")
            if res['isolate_stderr']:
                print(f"Isolate STDERR: {res['isolate_stderr']}")
        
        # Meta ma'lumotlarni ko'rsatish
        if res['meta']:
            print(f"\n📈 Meta info:")
            for line in res['meta'].split('\n'):
                if line.strip():
                    print(f"  {line}")
    
    except Exception as e:
        print(f"💥 KRITIK XATO: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        iso.cleanup()
        print(f"🧹 Tozalandi\n")


if __name__ == "__main__":
    # Test kodlari
    test_language("python", "print('Python ishlayapti! ✓')")
    
    test_language("javascript", "console.log('JavaScript ishlayapti! ✓');")
    
    test_language("typescript", 
        "const msg: string = 'TypeScript ishlayapti! ✓';\nconsole.log(msg);")
    
    test_language("cpp", """
#include <iostream>
int main() {
    std::cout << "C++ ishlayapti! ✓" << std::endl;
    return 0;
}
""")
    
    test_language("java", """
public class Solution {
    public static void main(String[] args) {
        System.out.println("Java ishlayapti! ✓");
    }
}
""")
    
    test_language("go", """
package main
import "fmt"
func main() {
    fmt.Println("Go ishlayapti! ✓")
}
""")