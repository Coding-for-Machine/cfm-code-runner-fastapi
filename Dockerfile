# Ubuntu 22.04 asosida
FROM ubuntu:22.04

# Interaktiv so'rovlarni o'chirish
ENV DEBIAN_FRONTEND=noninteractive

# Kerakli paketlarni va dasturlash tillarini o'rnatish
RUN apt-get update && apt-get install -y \
    build-essential \
    libcap-dev \
    pkg-config \
    git \
    python3 \
    python3-pip \
    golang \
    curl \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Node.js va TypeScript o'rnatish
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL deb.nodesource.com | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] deb.nodesource.com nodistro main" | tee /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get install -y nodejs && \
    npm install -g typescript

# Isolate-ni o'rnatish
RUN git clone github.com /tmp/isolate && \
    cd /tmp/isolate && \
    make install && \
    rm -rf /tmp/isolate

# Isolate uchun kerakli papka va ruxsatlar
RUN mkdir -p /var/local/lib/isolate

# Ishchi katalog
WORKDIR /app

# Python skriptingizni konteynerga nusxalash
COPY . .

# Isolate-ga SUID ruxsatini berish (Sandboks ishlashi uchun shart)
RUN chmod +s /usr/local/bin/isolate

# Konteynerni ishga tushirish (bash orqali)
CMD ["bash"]
