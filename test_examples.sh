#!/bin/bash

# CFM Code Runner - Test Examples
# Turli xil test misollar

API_URL="http://localhost:8080"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║        CFM Code Runner - Test Examples                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Ranglar
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Helper function
run_test() {
    local name=$1
    local json=$2
    echo -e "${BLUE}Testing: ${name}${NC}"
    echo "$json" | python3 -m json.tool > /tmp/request.json
    curl -s -X POST ${API_URL}/api/submit \
        -H "Content-Type: application/json" \
        -d @/tmp/request.json | python3 -m json.tool
    echo ""
    echo "─────────────────────────────────────────────────────────────"
    echo ""
}

# Test 1: Hello World (Python)
run_test "Python - Hello World" '{
  "source_code": "print(\"Hello, World!\")",
  "language": "python",
  "time_limit": 1.0
}'

# Test 2: Sum with Input (Python)
run_test "Python - Sum with Input" '{
  "source_code": "a, b = map(int, input().split())\nprint(a + b)",
  "language": "python",
  "input_data": "10 20",
  "time_limit": 1.0
}'

# Test 3: Factorial (Python)
run_test "Python - Factorial" '{
  "source_code": "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n-1)\n\nn = int(input())\nprint(factorial(n))",
  "language": "python",
  "input_data": "10",
  "time_limit": 1.0
}'

# Test 4: C++ Hello World
run_test "C++ - Hello World" '{
  "source_code": "#include <iostream>\nusing namespace std;\n\nint main() {\n    cout << \"Hello from C++\" << endl;\n    return 0;\n}",
  "language": "cpp",
  "time_limit": 2.0
}'

# Test 5: C++ with Input
run_test "C++ - Sum Array" '{
  "source_code": "#include <iostream>\nusing namespace std;\n\nint main() {\n    int n, sum = 0;\n    cin >> n;\n    for(int i = 0; i < n; i++) {\n        int x;\n        cin >> x;\n        sum += x;\n    }\n    cout << sum << endl;\n    return 0;\n}",
  "language": "cpp",
  "input_data": "5\n1 2 3 4 5",
  "time_limit": 2.0
}'

# Test 6: C Hello World
run_test "C - Hello World" '{
  "source_code": "#include <stdio.h>\n\nint main() {\n    printf(\"Hello from C\\n\");\n    return 0;\n}",
  "language": "c",
  "time_limit": 2.0
}'

# Test 7: Go Hello World
run_test "Go - Hello World" '{
  "source_code": "package main\n\nimport \"fmt\"\n\nfunc main() {\n    fmt.Println(\"Hello from Go\")\n}",
  "language": "go",
  "time_limit": 2.0
}'

# Test 8: Go with Input
run_test "Go - Fibonacci" '{
  "source_code": "package main\n\nimport \"fmt\"\n\nfunc fib(n int) int {\n    if n <= 1 {\n        return n\n    }\n    return fib(n-1) + fib(n-2)\n}\n\nfunc main() {\n    var n int\n    fmt.Scan(&n)\n    fmt.Println(fib(n))\n}",
  "language": "go",
  "input_data": "10",
  "time_limit": 2.0
}'

# Test 9: Runtime Error Test
run_test "Runtime Error Test" '{
  "source_code": "x = 1 / 0",
  "language": "python",
  "time_limit": 1.0
}'

# Test 10: Compilation Error Test
run_test "Compilation Error Test" '{
  "source_code": "#include <iostream>\nint main() {\n    cout << \"Missing semicolon\"\n    return 0;\n}",
  "language": "cpp",
  "time_limit": 2.0
}'

# Test 11: Time Limit Test
echo -e "${YELLOW}Warning: This test will take time (TLE test)${NC}"
run_test "Time Limit Exceeded Test" '{
  "source_code": "while True:\n    pass",
  "language": "python",
  "time_limit": 1.0
}'

# Test 12: Batch Test
echo -e "${BLUE}Testing: Batch Submit${NC}"
curl -s -X POST ${API_URL}/api/batch \
    -H "Content-Type: application/json" \
    -d '{
  "source_code": "n = int(input())\nprint(n * 2)",
  "language": "python",
  "test_cases": [
    {"input": "1", "expected_output": "2"},
    {"input": "5", "expected_output": "10"},
    {"input": "10", "expected_output": "20"},
    {"input": "100", "expected_output": "200"}
  ],
  "time_limit": 1.0
}' | python3 -m json.tool

echo ""
echo -e "${GREEN}✅ All tests completed!${NC}"
