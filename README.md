# CFM Code Runner - Isolate Docker

Docker konteynerida **Isolate sandbox** orqali Python, C++, C, va Go dasturlarini xavfsiz bajarish REST API tizimi.

## 📁 Loyiha tuzilishi

```
cfm-code-runner-flask/
├── Dockerfile              # Docker image
├── docker-compose.yml      # Docker Compose
├── Makefile               # Build buyruqlari
├── requirements.txt       # Python dependencies
├── main.py               # FastAPI server (asosiy fayl)
├── isolate_runner.py     # Isolate runner (subprocess)
├── README.md            # Dokumentatsiya
└── sendbocx.md         # Qo'shimcha ma'lumot
```

## 🚀 Tez boshlash

### 1. Talablar

- Docker 20.10+
- Docker Compose 1.29+
- 2GB+ RAM
- Linux kernel 3.10+

### 2. O'rnatish

```bash
# Repositoriyani klonlash
git clone <repository-url>
cd cfm-code-runner-flask

# Docker image yaratish va ishga tushirish
make build
make up

# Yoki bitta buyruq bilan
make rebuild
```

### 3. Tekshirish

```bash
# API holatini tekshirish
make health

# Statistikani ko'rish
make stats

# Barcha testlarni ishlatish
make test-all
```

## 📖 API Dokumentatsiyasi

### Base URL
```
http://localhost:8080
```

### Swagger UI
```
http://localhost:8080/docs
```

### ReDoc
```
http://localhost:8080/redoc
```

## 🔌 API Endpoints

### 1. Health Check

```bash
GET /health
```

**Curl:**
```bash
curl http://localhost:8080/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-03T10:30:00",
  "available_boxes": 95,
  "in_use_boxes": 5,
  "total_boxes": 100
}
```

### 2. Bitta Kod Bajarish

```bash
POST /api/submit
```

**Python misol:**
```bash
curl -X POST http://localhost:8080/api/submit \
  -H "Content-Type: application/json" \
  -d '{
    "source_code": "n = int(input())\nprint(n ** 2)",
    "language": "python",
    "input_data": "5",
    "time_limit": 1.0,
    "memory_limit": 262144
  }'
```

**Response:**
```json
{
  "status": "OK",
  "time": 0.023,
  "memory": 8192,
  "exit_code": 0,
  "stdout": "25\n",
  "stderr": "",
  "message": "",
  "timestamp": "2025-10-03T10:30:15"
}
```

**C++ misol:**
```bash
curl -X POST http://localhost:8080/api/submit \
  -H "Content-Type: application/json" \
  -d '{
    "source_code": "#include <iostream>\nusing namespace std;\n\nint main() {\n    int n;\n    cin >> n;\n    cout << n * n << endl;\n    return 0;\n}",
    "language": "cpp",
    "input_data": "10",
    "time_limit": 2.0,
    "memory_limit": 262144
  }'
```

### 3. Batch Test (Ko'p test case)

```bash
POST /api/batch
```

**Request:**
```bash
curl -X POST http://localhost:8080/api/batch \
  -H "Content-Type: application/json" \
  -d '{
    "source_code": "a, b = map(int, input().split())\nprint(a + b)",
    "language": "python",
    "test_cases": [
      {"input": "1 2", "expected_output": "3"},
      {"input": "10 20", "expected_output": "30"},
      {"input": "100 200", "expected_output": "300"}
    ],
    "time_limit": 1.0,
    "memory_limit": 262144
  }'
```

**Response:**
```json
{
  "total_tests": 3,
  "passed_tests": 3,
  "failed_tests": 0,
  "total_time": 0.045,
  "average_time": 0.015,
  "results": [
    {
      "test_number": 1,
      "status": "OK",
      "time": 0.015,
      "memory": 7680,
      "stdout": "3\n",
      "stderr": "",
      "input_data": "1 2",
      "expected_output": "3",
      "passed": true,
      "message": ""
    }
  ]
}
```

## 🛠️ Makefile Buyruqlari

### Asosiy buyruqlar
```bash
make help          # Barcha buyruqlarni ko'rsatish
make build         # Docker image yaratish
make up            # Ishga tushirish
make down          # To'xtatish
make restart       # Qayta ishga tushirish
make logs          # Loglarni ko'rish
make shell         # Bash shell
make stats         # Statistika
make health        # Health check
```

### Test buyruqlari
```bash
make test-python   # Python test
make test-cpp      # C++ test
make test-c        # C test
make test-go       # Go test
make test-input    # Input bilan test
make test-batch    # Batch test
make test-tle      # Time limit test
make test-all      # Barcha testlar
```

### Utility
```bash
make clean         # Hamma narsani o'chirish
make rebuild       # Qayta qurish
make ps            # Konteyner holati
make cleanup-boxes # Box larni tozalash
make benchmark     # Performance test
```

## 💻 Kod Misollari

### Python

```python
# Oddiy print
{
  "source_code": "print('Hello, World!')",
  "language": "python",
  "time_limit": 1.0
}

# Input bilan
{
  "source_code": "n = int(input())\nprint(sum(range(1, n+1)))",
  "language": "python",
  "input_data": "100",
  "time_limit": 1.0
}
```

### C++

```json
{
  "source_code": "#include <iostream>\nusing namespace std;\n\nint main() {\n    int n;\n    cin >> n;\n    cout << \"Result: \" << n * 2 << endl;\n    return 0;\n}",
  "language": "cpp",
  "input_data": "42",
  "time_limit": 2.0,
  "memory_limit": 262144
}
```

### C

```json
{
  "source_code": "#include <stdio.h>\n\nint main() {\n    int n;\n    scanf(\"%d\", &n);\n    printf(\"%d\\n\", n * n);\n    return 0;\n}",
  "language": "c",
  "input_data": "5",
  "time_limit": 2.0
}
```

### Go

```json
{
  "source_code": "package main\n\nimport \"fmt\"\n\nfunc main() {\n    var n int\n    fmt.Scan(&n)\n    fmt.Printf(\"Square: %d\\n\", n*n)\n}",
  "language": "go",
  "input_data": "7",
  "time_limit": 2.0
}
```

## ⚙️ Parametrlar

### Time Limit
- **Minimum:** 0.1 soniya
- **Maksimum:** 10 soniya
- **Default:** 1.0 soniya
- CPU vaqtini cheklaydi

### Memory Limit
- **Minimum:** 32768 KB (32 MB)
- **Maksimum:** 1048576 KB (1 GB)
- **Default:** 262144 KB (256 MB)

### Qo'llab-quvvatlanadigan tillar
- **python** - Python 3.11
- **cpp** - C++ (g++ 11.4, std=c++17)
- **c** - C (gcc 11.4, std=c11)
- **go** - Go 1.21.5

## 📊 Status Kodlari

| Status | Tavsif |
|--------|--------|
| `OK` | Muvaffaqiyatli bajarildi |
| `RE` | Runtime Error (dastur xatosi) |
| `TLE` | Time Limit Exceeded |
| `MLE` | Memory Limit Exceeded |
| `CE` | Compilation Error |
| `IE` | Internal Error |

## 🐛 Muammolarni Hal Qilish

### Konteyner ishlamayapti

```bash
# Loglarni tekshirish
make logs

# Konteyner holatini ko'rish
make ps

# Qayta ishga tushirish
make restart
```

### Permission denied

```bash
# docker-compose.yml da privileged: true borligini tekshiring
# Yoki sudo bilan ishga tushiring
sudo make up
```

### Box ID mavjud emas

```bash
# Barcha box larni tozalash
make cleanup-boxes

# Yoki konteynerga kirib qo'lda
make shell
for i in {0..99}; do isolate --box-id=$i --cleanup 2>/dev/null; done
```

### API javob bermayapti

```bash
# Health check
make health

# Loglarni ko'rish
make logs-tail

# Qayta qurish
make rebuild
```

## 🔒 Xavfsizlik

Isolate quyidagi xavfsizlik choralarini qo'llaydi:

1. **Namespace Isolation** - Jarayonlar alohida namespace da
2. **Cgroup** - Resurs cheklash (CPU, xotira)
3. **Seccomp** - System call filterlash
4. **Chroot** - Fayl tizimini cheklash
5. **Time & Memory Limits** - Har bir kod uchun limit

## 📈 Performance

### Box Pool
- 100 ta box mavjud
- Parallel bajarilish qo'llab-quvvatlanadi
- Har bir box alohida izolatsiyalangan

### Response Time
- Python: ~50-100ms
- C/C++: ~100-200ms (compile + run)
- Go: ~150-250ms (compile + run)

### Throughput
- 100+ requests/second (parallel)
- Box pool bilan cheklanadi

## 🧪 Test Qilish

### Oddiy test

```bash
# Barcha tillarni test qilish
make test-all
```

### Manual test

```bash
# Python
curl -X POST http://localhost:8080/api/submit \
  -H "Content-Type: application/json" \
  -d '{"source_code": "print(42)", "language": "python"}'

# C++
curl -X POST http://localhost:8080/api/submit \
  -H "Content-Type: application/json" \
  -d '{"source_code": "#include <iostream>\nint main(){std::cout<<42;}", "language": "cpp"}'
```

### Performance test

```bash
make benchmark
```

## 📝 Development

### Local development

```bash
# Konteynerga kirish
make shell

# Python shell
make shell-python

# Isolate test
isolate --version
isolate --box-id=0 --init
```

### Kod o'zgartirish

1. Kodni o'zgartiring (`main.py`, `isolate_runner.py`)
2. Qayta quring: `make rebuild`
3. Test qiling: `make test-all`

## 🤝 Contributing

1. Fork qiling
2. Branch yarating: `git checkout -b feature/amazing`
3. Commit qiling: `git commit -m 'Add amazing feature'`
4. Push qiling: `git push origin feature/amazing`
5. Pull Request oching

## 📄 License

MIT License

## 👥 Authors

CFM Code Runner Team

## 🔗 Links

- [Isolate GitHub](https://github.com/ioi/isolate)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Docker Docs](https://docs.docker.com/)

## ❓ FAQ

**Q: Nima uchun privileged rejim kerak?**  
A: Isolate namespace va cgroup yaratish uchun privileged access kerak.

**Q: Maksimal vaqt limiti nima uchun 10 soniya?**  
A: DDoS va abuse oldini olish uchun.

**Q: Java qo'llab-quvvatlanadimi?**  
A: Hozircha yo'q, lekin qo'shish mumkin.

**Q: Production uchun tayyormi?**  
A: Ha, lekin monitoring va load balancing qo'shing.

## 📞 Support

Muammolar bo'lsa, issue oching yoki email yuboring.