# Production Deployment Guide

CFM Code Runner ni production muhitida ishlatish uchun qo'llanma.

## 📋 Production Checklist

### 1. Server Talablari

**Minimal:**
- CPU: 4 cores
- RAM: 8 GB
- Disk: 50 GB SSD
- OS: Ubuntu 22.04 LTS

**Tavsiya etilgan:**
- CPU: 8+ cores
- RAM: 16+ GB
- Disk: 100 GB SSD
- OS: Ubuntu 22.04 LTS

### 2. Xavfsizlik Sozlamalari

#### Firewall

```bash
# UFW o'rnatish
sudo apt-get install ufw

# Kerakli portlarni ochish
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 8080/tcp  # API

# Yoqish
sudo ufw enable
```

#### HTTPS (SSL/TLS)

Production da SSL/TLS ishlatish majburiy!

**Nginx Reverse Proxy:**

```nginx
# /etc/nginx/sites-available/code-runner

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeout sozlamalari
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

**Let's Encrypt SSL sertifikat:**

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 3. Environment Variables

Production `.env` fayli:

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8080
LOG_LEVEL=WARNING

# Isolate Configuration
MAX_BOXES=200
DEFAULT_TIME_LIMIT=2.0
DEFAULT_MEMORY_LIMIT=262144

# Security
MAX_SOURCE_CODE_SIZE=65536
MAX_INPUT_SIZE=10240
ENABLE_RATE_LIMIT=true
RATE_LIMIT=100  # requests per minute

# Performance
WORKER_COUNT=4
THREAD_POOL_SIZE=50

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090
```

### 4. Docker Compose (Production)

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  code-runner:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: cfm-code-runner-prod
    privileged: true
    restart: always
    
    volumes:
      - ./logs:/app/logs
      - /sys/fs/cgroup:/sys/fs/cgroup:ro
    
    ports:
      - "127.0.0.1:8080:8080"  # Faqat localhost
    
    environment:
      - PYTHONUNBUFFERED=1
      - LOG_LEVEL=WARNING
    
    env_file:
      - .env.production
    
    security_opt:
      - apparmor=unconfined
    
    cap_add:
      - SYS_ADMIN
      - SYS_PTRACE
    
    deploy:
      resources:
        limits:
          cpus: '8'
          memory: 16G
        reservations:
          cpus: '4'
          memory: 8G
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "10"
```

### 5. Monitoring

#### Prometheus Metrics

`metrics.py` faylini qo'shing:

```python
from prometheus_client import Counter, Histogram, Gauge
from prometheus_client import start_http_server

# Metrics
request_count = Counter('code_runner_requests_total', 'Total requests', ['language', 'status'])
request_duration = Histogram('code_runner_request_duration_seconds', 'Request duration')
active_boxes = Gauge('code_runner_active_boxes', 'Active boxes')
available_boxes = Gauge('code_runner_available_boxes', 'Available boxes')

def start_metrics_server(port=9090):
    start_http_server(port)
```

#### Grafana Dashboard

Prometheus + Grafana orqali monitoring:

1. Prometheus o'rnatish
2. Grafana o'rnatish
3. Dashboard yaratish

### 6. Logging

Production logging sozlamalari:

```python
# main.py da
import logging
from logging.handlers import RotatingFileHandler

# File handler
file_handler = RotatingFileHandler(
    '/app/logs/api.log',
    maxBytes=100*1024*1024,  # 100MB
    backupCount=10
)

# Format
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
file_handler.setFormatter(formatter)

# Logger
logger = logging.getLogger()
logger.addHandler(file_handler)
logger.setLevel(logging.WARNING)
```

### 7. Rate Limiting

FastAPI rate limiting:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/submit")
@limiter.limit("10/minute")
async def submit_code(request: Request, submission: SubmissionRequest):
    # ...
```

### 8. Backup va Recovery

#### Automated Backup

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Code backup
tar -czf ${BACKUP_DIR}/code_${DATE}.tar.gz /app

# Logs backup
tar -czf ${BACKUP_DIR}/logs_${DATE}.tar.gz /app/logs

# Database backup (agar bo'lsa)
# ...

# Eski backup larni o'chirish (30 kundan eski)
find ${BACKUP_DIR} -name "*.tar.gz" -mtime +30 -delete
```

#### Cron job

```bash
# crontab -e
0 2 * * * /root/backup.sh
```

### 9. Load Balancing

Nginx load balancer:

```nginx
upstream code_runner_backend {
    least_conn;
    server 127.0.0.1:8080 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8081 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8082 max_fails=3 fail_timeout=30s;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    location / {
        proxy_pass http://code_runner_backend;
        # ...
    }
}
```

### 10. Auto-restart va Health Monitoring

#### Systemd service

```ini
# /etc/systemd/system/code-runner.service

[Unit]
Description=CFM Code Runner Service
After=docker.service
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=/opt/code-runner
ExecStart=/usr/local/bin/docker-compose up
ExecStop=/usr/local/bin/docker-compose down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable code-runner
sudo systemctl start code-runner
sudo systemctl status code-runner
```

## 🔄 Deployment Process

### 1. Birinchi marta deploy

```bash
# Serverni yangilash
sudo apt-get update && sudo apt-get upgrade -y

# Docker o'rnatish
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Docker Compose o'rnatish
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Code klonlash
git clone <repository> /opt/code-runner
cd /opt/code-runner

# Environment sozlash
cp .env.example .env.production
nano .env.production

# Build va run
docker-compose -f docker-compose.prod.yml up -d --build

# Loglarni tekshirish
docker-compose -f docker-compose.prod.yml logs -f
```

### 2. Yangilash (Update)

```bash
cd /opt/code-runner

# Yangi kodlarni olish
git pull

# Qayta build qilish
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build

# Health check
curl http://localhost:8080/health
```

### 3. Rollback

```bash
# Eski versiyaga qaytish
git checkout <previous-commit>
docker-compose -f docker-compose.prod.yml up -d --build
```

## 📊 Performance Tuning

### 1. Box Count Optimization

```python
# Optimal box count formula:
# boxes = (CPU_cores * 2) + 2

# 8 core server uchun:
MAX_BOXES = 18
```

### 2. Worker Count

```python
# Worker count formula:
# workers = (CPU_cores * 2) + 1

# Uvicorn sozlash
uvicorn.run(
    "main:app",
    host="0.0.0.0",
    port=8080,
    workers=17,  # 8 * 2 + 1
    loop="uvloop"
)
```

### 3. Database Connection Pool (agar kerak bo'lsa)

```python
DATABASE_POOL_SIZE = 20
DATABASE_MAX_OVERFLOW = 10
```

## 🚨 Monitoring Alerts

### Telegram Alert Bot

```python
import requests

def send_telegram_alert(message):
    bot_token = "YOUR_BOT_TOKEN"
    chat_id = "YOUR_CHAT_ID"
    url = f"https://api