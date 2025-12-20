#!/bin/bash
set -e

echo "=================================================="
echo "🚀 Code Runner - Starting..."
echo "=================================================="

# =====================================================
# ISOLATE CLEANUP (MUHIM!)
# =====================================================
echo "[1/4] Cleaning up old isolate boxes..."

# Barcha eski box'larni tozalash
for i in {0..999}; do
    if [ -d "/var/local/lib/isolate/$i" ]; then
        echo "  - Cleaning box $i..."
        isolate --box-id=$i --cleanup 2>/dev/null || true
        rm -rf /var/local/lib/isolate/$i/* 2>/dev/null || true
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

# Cleanup test box
isolate --box-id=$TEST_BOX --cleanup 2>/dev/null || true
rm -rf /var/local/lib/isolate/$TEST_BOX 2>/dev/null || true

# Init
isolate --box-id=$TEST_BOX --init >/dev/null 2>&1 || { 
    echo "❌ Isolate init failed!"; 
    exit 1; 
}

# Write test code
echo 'print("Isolate works!")' > /var/local/lib/isolate/$TEST_BOX/box/test.py

# Run test
isolate --box-id=$TEST_BOX --run \
    --time=1 --mem=262144 \
    --stdout=/var/local/lib/isolate/$TEST_BOX/box/out.txt \
    --stderr=/var/local/lib/isolate/$TEST_BOX/box/err.txt \
    --meta=/var/local/lib/isolate/$TEST_BOX/meta.txt \
    -- /usr/bin/python3 test.py >/dev/null 2>&1 || {
        echo "❌ Isolate run failed!"
        exit 1
    }

# Check output
if grep -q "Isolate works!" /var/local/lib/isolate/$TEST_BOX/box/out.txt 2>/dev/null; then
    echo "  ✓ Isolate test passed"
else
    echo "❌ Isolate test failed!"
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