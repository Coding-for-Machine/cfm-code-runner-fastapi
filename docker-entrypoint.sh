#!/bin/bash
set -e

echo "=================================================="
echo "🚀 Code Runner - Starting..."
echo "=================================================="

# =====================================================
# ISOLATE CLEANUP (MUHIM!)
# =====================================================
echo "[1/4] Cleaning up old isolate boxes..."

# Check if isolate directory is on tmpfs
MOUNT_TYPE=$(df -T /var/local/lib/isolate 2>/dev/null | tail -1 | awk '{print $2}')
if [ "$MOUNT_TYPE" = "tmpfs" ]; then
    echo "  ✓ Isolate is on tmpfs (optimal)"
else
    echo "  ⚠️  Warning: Isolate is on $MOUNT_TYPE (may cause issues)"
    echo "  Recommendation: Use --tmpfs /var/local/lib/isolate:exec,mode=777"
fi

# Barcha eski box'larni tozalash
for i in {0..999}; do
    if [ -d "/var/local/lib/isolate/$i" ]; then
        isolate --box-id=$i --cleanup 2>/dev/null || true
        rm -rf /var/local/lib/isolate/$i 2>/dev/null || true
    fi
done

echo "  ✓ Cleanup complete"

# =====================================================
# DIRECTORY PERMISSIONS
# =====================================================
echo "[2/4] Setting up permissions..."

# Isolate directory
mkdir -p /var/local/lib/isolate
chmod 755 /var/local/lib/isolate

echo "  ✓ Permissions set"

# =====================================================
# VERIFY INSTALLATIONS
# =====================================================
echo "[3/4] Verifying installations..."

# Python
python3 --version || { echo "❌ Python not found!"; exit 1; }

# GCC/G++
gcc --version >/dev/null 2>&1 || { echo "❌ GCC not found!"; exit 1; }
g++ --version >/dev/null 2>&1 || { echo "❌ G++ not found!"; exit 1; }

# Java
java --version >/dev/null 2>&1 || { echo "❌ Java not found!"; exit 1; }
javac --version >/dev/null 2>&1 || { echo "❌ Javac not found!"; exit 1; }

# Go
go version >/dev/null 2>&1 || { echo "❌ Go not found!"; exit 1; }

# Node.js
node --version >/dev/null 2>&1 || { echo "❌ Node.js not found!"; exit 1; }

# TypeScript
tsc --version >/dev/null 2>&1 || { echo "⚠️  TypeScript not found (optional)"; }

# Isolate
isolate --version >/dev/null 2>&1 || { echo "❌ Isolate not found!"; exit 1; }

echo "  ✓ All tools verified"

# =====================================================
# TEST ISOLATE
# =====================================================
echo "[4/4] Testing isolate..."

TEST_BOX=999

# MUHIM: Cleanup va to'liq tozalash
echo "  - Cleaning test box..."
isolate --box-id=$TEST_BOX --cleanup 2>/dev/null || true
rm -rf /var/local/lib/isolate/$TEST_BOX 2>/dev/null || true

# Biroz kutish (filesystem sync uchun)
sleep 0.5

# Init
echo "  - Initializing box $TEST_BOX..."
if ! isolate --box-id=$TEST_BOX --init >/dev/null 2>&1; then
    echo "❌ Isolate init failed!"
    isolate --box-id=$TEST_BOX --init  # Show error
    exit 1
fi

# Verify box is clean
if [ "$(ls -A /var/local/lib/isolate/$TEST_BOX/box/ 2>/dev/null)" ]; then
    echo "⚠️  Warning: Box is not empty after init!"
    echo "  Contents: $(ls -la /var/local/lib/isolate/$TEST_BOX/box/)"
    # Clean it manually
    rm -rf /var/local/lib/isolate/$TEST_BOX/box/* 2>/dev/null || true
fi

# NOW write test code
echo "  - Writing test code..."
echo 'print("Isolate works!")' > /var/local/lib/isolate/$TEST_BOX/box/test.py

# Verify test file was created
if [ ! -f /var/local/lib/isolate/$TEST_BOX/box/test.py ]; then
    echo "❌ Failed to create test file!"
    exit 1
fi

# Run test with detailed output
echo "  - Running test code..."
if ! isolate --box-id=$TEST_BOX --run \
    --share-net \
    --time=1 --mem=262144 \
    --stdout=/var/local/lib/isolate/$TEST_BOX/box/out.txt \
    --stderr=/var/local/lib/isolate/$TEST_BOX/box/err.txt \
    --meta=/var/local/lib/isolate/$TEST_BOX/meta.txt \
    -- /usr/bin/python3 test.py 2>&1; then
    
    echo "❌ Isolate run failed!"
    echo ""
    echo "Debug info:"
    echo "  Box directory exists: $([ -d /var/local/lib/isolate/$TEST_BOX ] && echo 'yes' || echo 'no')"
    echo "  Test file exists: $([ -f /var/local/lib/isolate/$TEST_BOX/box/test.py ] && echo 'yes' || echo 'no')"
    echo "  Python path: $(which python3)"
    echo ""
    echo "Stderr:"
    cat /var/local/lib/isolate/$TEST_BOX/box/err.txt 2>/dev/null || echo "(empty)"
    echo ""
    echo "Meta:"
    cat /var/local/lib/isolate/$TEST_BOX/meta.txt 2>/dev/null || echo "(not found)"
    
    # Try running without isolate
    echo ""
    echo "Testing Python directly:"
    /usr/bin/python3 /var/local/lib/isolate/$TEST_BOX/box/test.py 2>&1 || echo "Python also failed!"
    
    exit 1
fi

# Check output
if [ -f /var/local/lib/isolate/$TEST_BOX/box/out.txt ]; then
    OUTPUT=$(cat /var/local/lib/isolate/$TEST_BOX/box/out.txt 2>/dev/null)
    if echo "$OUTPUT" | grep -q "Isolate works!"; then
        echo "  ✓ Isolate test passed"
    else
        echo "❌ Output mismatch!"
        echo "  Expected: 'Isolate works!'"
        echo "  Got: '$OUTPUT'"
        exit 1
    fi
else
    echo "❌ Output file not created!"
    exit 1
fi

# Cleanup
isolate --box-id=$TEST_BOX --cleanup 2>/dev/null || true
rm -rf /var/local/lib/isolate/$TEST_BOX 2>/dev/null || true

# =====================================================
# START APPLICATION
# =====================================================
echo "=================================================="
echo "✅ All checks passed! Starting application..."
echo "=================================================="
echo ""

# Execute the main command
exec "$@"