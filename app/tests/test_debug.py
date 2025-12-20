#!/usr/bin/env python3
"""
Simple test script - xatolarni topish uchun
"""

import asyncio
import sys
from pathlib import Path

# PYTHONPATH sozlash (agar kerak bo'lsa)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print(f"[INFO] Project root: {project_root}")
print(f"[INFO] Python path: {sys.path}")

# ==================== STEP 1: IMPORT TEKSHIRISH ====================
print("\n" + "="*60)
print("STEP 1: Import tekshirish...")
print("="*60)

try:
    from core.runner import execute_code
    print("[✓] core.runner import muvaffaqiyatli")
except ImportError as e:
    print(f"[✗] Import xatosi: {e}")
    print("\nYechim:")
    print("  1. cd ~/Desktop/code-runner")
    print("  2. ls -la core/")
    print("  3. Fayllar mavjudligini tekshiring:")
    print("     - core/__init__.py")
    print("     - core/runner.py")
    print("     - core/isolate.py")
    print("     - core/box_manager.py")
    sys.exit(1)

try:
    from core.box_manager import BoxManager
    print("[✓] core.box_manager import muvaffaqiyatli")
except ImportError as e:
    print(f"[✗] Import xatosi: {e}")
    sys.exit(1)

try:
    from core.isolate import Isolate, LANGUAGE_CONFIGS
    print("[✓] core.isolate import muvaffaqiyatli")
except ImportError as e:
    print(f"[✗] Import xatosi: {e}")
    sys.exit(1)

# ==================== STEP 2: ISOLATE MAVJUDLIGI ====================
print("\n" + "="*60)
print("STEP 2: Isolate mavjudligini tekshirish...")
print("="*60)

import subprocess
try:
    result = subprocess.run(
        ["isolate", "--version"],
        capture_output=True,
        timeout=2
    )
    print(f"[✓] Isolate o'rnatilgan: {result.stdout.decode().strip()}")
except FileNotFoundError:
    print("[✗] Isolate topilmadi!")
    print("\nYechim:")
    print("  sudo apt update")
    print("  sudo apt install -y isolate")
    sys.exit(1)
except Exception as e:
    print(f"[✗] Xato: {e}")
    sys.exit(1)

# ==================== STEP 3: LANGUAGE CONFIGS ====================
print("\n" + "="*60)
print("STEP 3: Language configs tekshirish...")
print("="*60)

for lang, config in LANGUAGE_CONFIGS.items():
    print(f"\n[{lang}]")
    print(f"  File: {config['file']}")
    print(f"  Run: {' '.join(config['run'])}")
    
    # Kompilyator mavjudligini tekshirish
    if config['compile']:
        compiler = config['compile'][0]
        try:
            result = subprocess.run(
                [compiler, "--version"],
                capture_output=True,
                timeout=2
            )
            print(f"  [✓] Compiler mavjud: {compiler}")
        except FileNotFoundError:
            print(f"  [✗] Compiler topilmadi: {compiler}")
        except Exception as e:
            print(f"  [?] Tekshirish xatosi: {e}")
    else:
        # Interpreter tekshirish
        interpreter = config['run'][0]
        try:
            result = subprocess.run(
                [interpreter, "--version"],
                capture_output=True,
                timeout=2
            )
            print(f"  [✓] Interpreter mavjud: {interpreter}")
        except FileNotFoundError:
            print(f"  [✗] Interpreter topilmadi: {interpreter}")
        except Exception as e:
            print(f"  [?] Tekshirish xatosi: {e}")

# ==================== STEP 4: SIMPLE TEST ====================
print("\n" + "="*60)
print("STEP 4: Oddiy Python test...")
print("="*60)

async def test_python():
    try:
        print("\n[TEST] Python Hello World")
        result = await execute_code(
            language="python",
            code='print("Hello from Python!")',
            test_input="",
            expected_output="Hello from Python!"
        )
        
        print(f"\n  Status: {result['status']}")
        print(f"  Message: {result['message']}")
        print(f"  Time: {result['time']}s")
        print(f"  Memory: {result['memory_kb']}KB")
        print(f"  Stdout: {result['stdout']}")
        print(f"  Stderr: {result['stderr']}")
        print(f"  Is Accepted: {result['is_accepted']}")
        
        if result['status'] == 'OK' and result['is_accepted']:
            print("\n[✓] TEST PASSED!")
            return True
        else:
            print(f"\n[✗] TEST FAILED!")
            print(f"  Expected status: OK")
            print(f"  Got status: {result['status']}")
            return False
            
    except Exception as e:
        print(f"\n[✗] Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

# ==================== STEP 5: INPUT BILAN TEST ====================
async def test_python_input():
    try:
        print("\n[TEST] Python with input")
        result = await execute_code(
            language="python",
            code='a, b = map(int, input().split())\nprint(a + b)',
            test_input="3 7",
            expected_output="10"
        )
        
        print(f"\n  Status: {result['status']}")
        print(f"  Stdout: {result['stdout']}")
        print(f"  Is Accepted: {result['is_accepted']}")
        
        if result['status'] == 'OK' and result['is_accepted']:
            print("\n[✓] TEST PASSED!")
            return True
        else:
            print(f"\n[✗] TEST FAILED!")
            return False
            
    except Exception as e:
        print(f"\n[✗] Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

# ==================== STEP 6: MANUAL ISOLATE TEST ====================
print("\n" + "="*60)
print("STEP 6: Manual Isolate test...")
print("="*60)

try:
    print("\n[MANUAL] Isolate init...")
    subprocess.run(["isolate", "--box-id=999", "--init"], check=True)
    
    print("[MANUAL] Kod yozish...")
    with open("/var/local/lib/isolate/999/box/test.py", "w") as f:
        f.write('print("Manual test")')
    
    print("[MANUAL] Bajarish...")
    subprocess.run([
        "isolate", "--box-id=999", "--run",
        "--time=2", "--mem=524288",
        "--stdout=out.txt", "--stderr=err.txt", "--meta=meta.txt",
        "--", "/usr/bin/python3", "test.py"
    ], check=True, cwd="/var/local/lib/isolate/999")
    
    print("[MANUAL] Output o'qish...")
    with open("/var/local/lib/isolate/999/box/out.txt") as f:
        output = f.read()
        print(f"  Output: {output}")
    
    with open("/var/local/lib/isolate/999/meta.txt") as f:
        meta = f.read()
        print(f"  Meta: {meta[:100]}")
    
    print("[MANUAL] Cleanup...")
    subprocess.run(["isolate", "--box-id=999", "--cleanup"])
    
    print("\n[✓] MANUAL TEST PASSED!")
    
except Exception as e:
    print(f"\n[✗] Manual test failed: {e}")
    import traceback
    traceback.print_exc()

# ==================== RUN ASYNC TESTS ====================
print("\n" + "="*60)
print("STEP 7: Running async tests...")
print("="*60)

async def main():
    test1 = await test_python()
    test2 = await test_python_input()
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Python Hello: {'✓ PASSED' if test1 else '✗ FAILED'}")
    print(f"Python Input: {'✓ PASSED' if test2 else '✗ FAILED'}")
    
    if test1 and test2:
        print("\n🎉 BARCHA TESTLAR MUVAFFAQIYATLI!")
        return 0
    else:
        print("\n❌ BA'ZI TESTLAR MUVAFFAQIYATSIZ!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)