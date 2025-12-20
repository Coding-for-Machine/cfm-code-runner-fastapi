FROM ubuntu:22.04

# Interaktivlikni o'chirish va asosiy paketlarni o'rnatish
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    build-essential \
    libcap-dev \
    pkg-config \
    git \
    python3 \
    python3-pip \
    openjdk-17-jdk \
    golang \
    curl \
    sudo \
    && rm -rf /var/lib/apt/lists/*


# Node.js 20.x (LTS) va TypeScript o'rnatish - 2025-yilgi barqaror usul
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL deb.nodesource.com | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] deb.nodesource.com nodistro main" > /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get install -y nodejs && \
    npm install -g typescript

# Isolate sandboksini o'rnatish
RUN git clone github.com /tmp/isolate && \
    cd /tmp/isolate && \
    make install && \
    rm -rf /tmp/isolate && \
    chmod +s /usr/local/bin/isolate

# Isolate uchun kerakli tizim katalogini yaratish
RUN mkdir -p /var/local/lib/isolate

WORKDIR /app
COPY . .

CMD ["bash"]