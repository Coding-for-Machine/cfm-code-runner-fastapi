.PHONY: build up down logs test clean help shell stats

# Ranglar
GREEN=\033[0;32m
YELLOW=\033[1;33m
BLUE=\033[0;34m
RED=\033[0;31m
NC=\033[0m

IMAGE_NAME=cfm-code-runner
CONTAINER_NAME=cfm-code-runner
API_URL=http://localhost:8080

help: ## Barcha buyruqlarni ko'rsatish
	@echo "$(GREEN)╔═══════════════════════════════════════════════════╗$(NC)"
	@echo "$(GREEN)║     CFM Code Runner - Docker Commands             ║$(NC)"
	@echo "$(GREEN)╚═══════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

build: ## Docker image yaratish
	@echo "$(BLUE)🔨 Docker image yaratilmoqda...$(NC)"
	docker compose build --no-cache
	@echo "$(GREEN)✅ Image tayyor!$(NC)"

up: ## Konteynerni ishga tushirish
	@echo "$(BLUE)🚀 Konteyner ishga tushirilmoqda...$(NC)"
	docker compose up -d
	@sleep 3
	@echo ""
	@echo "$(GREEN)✅ Konteyner ishga tushdi!$(NC)"
	@echo "$(GREEN)📡 API: $(API_URL)$(NC)"
	@echo "$(GREEN)📖 Docs: $(API_URL)/docs$(NC)"
	@echo "$(GREEN)📊 Stats: $(API_URL)/stats$(NC)"
	@echo ""

down: ## Konteynerni to'xtatish
	@echo "$(YELLOW)⏹️  Konteyner to'xtatilmoqda...$(NC)"
	docker compose down
	@echo "$(GREEN)✅ To'xtatildi$(NC)"

restart: down up ## Qayta ishga tushirish

logs: ## Loglarni ko'rish (Ctrl+C bilan chiqish)
	@echo "$(BLUE)📋 Loglar (Ctrl+C bilan chiqish):$(NC)"
	docker compose logs -f

logs-tail: ## Oxirgi 100 ta log
	docker compose logs --tail=100

shell: ## Konteynerga kirish (bash)
	@echo "$(BLUE)🐚 Bash shell...$(NC)"
	docker exec -it $(CONTAINER_NAME) /bin/bash

shell-python: ## Python shell
	docker exec -it $(CONTAINER_NAME) python3

stats: ## API statistikasini ko'rish
	@echo "$(BLUE)📊 API Statistika:$(NC)"
	@curl -s $(API_URL)/stats | python3 -m json.tool

health: ## Health check
	@echo "$(BLUE)❤️  Health Check:$(NC)"
	@curl -s $(API_URL)/health | python3 -m json.tool

# ============= Test buyruqlari =============

test-python: ## Python kodini test qilish
	@echo "$(BLUE)🐍 Python test...$(NC)"
	@curl -s -X POST $(API_URL)/api/submit \
		-H "Content-Type: application/json" \
		-d '{"source_code": "print(\"Hello from Python!\")", "language": "python", "time_limit": 1.0}' \
		| python3 -m json.tool

test-cpp: ## C++ kodini test qilish
	@echo "$(BLUE)⚙️  C++ test...$(NC)"
	@curl -s -X POST $(API_URL)/api/submit \
		-H "Content-Type: application/json" \
		-d '{"source_code": "#include <iostream>\nint main() { std::cout << \"Hello from C++\" << std::endl; return 0; }", "language": "cpp", "time_limit": 2.0}' \
		| python3 -m json.tool

test-go: ## Go kodini test qilish
	@echo "$(BLUE)🔵 Go test...$(NC)"
	@curl -s -X POST $(API_URL)/api/submit \
		-H "Content-Type: application/json" \
		-d '{"source_code": "package main\nimport \"fmt\"\nfunc main() { fmt.Println(\"Hello from Go\") }", "language": "go", "time_limit": 2.0}' \
		| python3 -m json.tool

test-c: ## C kodini test qilish
	@echo "$(BLUE)🔧 C test...$(NC)"
	@curl -s -X POST $(API_URL)/api/submit \
		-H "Content-Type: application/json" \
		-d '{"source_code": "#include <stdio.h>\nint main() { printf(\"Hello from C\\n\"); return 0; }", "language": "c", "time_limit": 2.0}' \
		| python3 -m json.tool

test-input: ## Input bilan test
	@echo "$(BLUE)📝 Input test...$(NC)"
	@curl -s -X POST $(API_URL)/api/submit \
		-H "Content-Type: application/json" \
		-d '{"source_code": "n = int(input())\nprint(f\"Square: {n**2}\")", "language": "python", "input_data": "5", "time_limit": 1.0}' \
		| python3 -m json.tool

test-batch: ## Batch testini ishlatish
	@echo "$(BLUE)📦 Batch test...$(NC)"
	@curl -s -X POST $(API_URL)/api/batch \
		-H "Content-Type: application/json" \
		-d '{"source_code": "n = int(input())\nprint(n * 2)", "language": "python", "test_cases": [{"input": "5", "expected_output": "10"}, {"input": "10", "expected_output": "20"}, {"input": "100", "expected_output": "200"}]}' \
		| python3 -m json.tool

test-tle: ## Time Limit test
	@echo "$(BLUE)⏱️  TLE test...$(NC)"
	@curl -s -X POST $(API_URL)/api/submit \
		-H "Content-Type: application/json" \
		-d '{"source_code": "while True:\n    pass", "language": "python", "time_limit": 1.0}' \
		| python3 -m json.tool

test-all: test-python test-cpp test-c test-go test-input test-batch ## Barcha testlarni ishlatish

# ============= Utility buyruqlari =============

clean: ## Barcha narsalarni o'chirish
	@echo "$(YELLOW)🧹 Tozalanmoqda...$(NC)"
	docker compose down -v
	docker rmi $(IMAGE_NAME) 2>/dev/null || true
	rm -rf submissions results
	@echo "$(GREEN)✅ Tozalandi!$(NC)"

rebuild: clean build up ## To'liq qayta qurish

ps: ## Konteyner holatini ko'rish
	@echo "$(BLUE)📊 Docker containers:$(NC)"
	docker compose ps

inspect: ## Konteyner ma'lumotlari
	docker inspect $(CONTAINER_NAME) | python3 -m json.tool

cleanup-boxes: ## Barcha box larni tozalash
	@echo "$(YELLOW)🧹 Box larni tozalash...$(NC)"
	@docker exec $(CONTAINER_NAME) bash -c "for i in {0..99}; do isolate --box-id=\$$i --cleanup 2>/dev/null; done"
	@echo "$(GREEN)✅ Box lar tozalandi$(NC)"

# ============= Development =============

dev-setup: ## Development muhitini o'rnatish
	@echo "$(BLUE)⚙️  Development setup...$(NC)"
	mkdir -p submissions results
	chmod 777 submissions results
	@echo "$(GREEN)✅ Setup tayyor$(NC)"

format: ## Python kodni formatlash
	docker exec $(CONTAINER_NAME) black *.py 2>/dev/null || echo "black o'rnatilmagan"

lint: ## Python kodni tekshirish
	docker exec $(CONTAINER_NAME) flake8 *.py 2>/dev/null || echo "flake8 o'rnatilmagan"

watch: ## Real-time loglarni kuzatish
	@echo "$(BLUE)👀 Loglarni kuzatish (Ctrl+C bilan chiqish)$(NC)"
	docker compose logs -f --tail=50

# ============= Info =============

info: ## Tizim haqida ma'lumot
	@echo "$(GREEN)╔═══════════════════════════════════════════════════╗$(NC)"
	@echo "$(GREEN)║           CFM Code Runner - System Info           ║$(NC)"
	@echo "$(GREEN)╚═══════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(YELLOW)Docker:$(NC)"
	@docker --version
	@docker compose --version
	@echo ""
	@echo "$(YELLOW)Konteyner:$(NC)"
	@docker compose ps 2>/dev/null || echo "  Konteyner ishlamayapti"
	@echo ""
	@echo "$(YELLOW)API:$(NC)"
	@echo "  URL: $(API_URL)"
	@curl -s $(API_URL)/health 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "  API ishlamayapti"

benchmark: ## Performance test
	@echo "$(BLUE)⚡ Performance test...$(NC)"
	@for i in {1..10}; do \
		echo "Request $$i..."; \
		time curl -s -X POST $(API_URL)/api/submit \
			-H "Content-Type: application/json" \
			-d '{"source_code": "print(42)", "language": "python"}' > /dev/null; \
	done
	@echo "$(GREEN)✅ Benchmark tugadi$(NC)"