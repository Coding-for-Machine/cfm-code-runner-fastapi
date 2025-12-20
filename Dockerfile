# =====================================================
# STAGE 1: BASE IMAGE
# =====================================================
FROM ubuntu:22.04 AS base

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# Tizimni yangilash
RUN apt-get update && apt-get upgrade -y

# =====================================================
# STAGE 2: BUILD TOOLS
# =====================================================
FROM base AS builder

# Build tools
RUN apt-get install -y \
    build-essential \
    gcc \
    g++ \
    make \
    pkg-config \
    libcap-dev \
    libsystemd-dev \
    git \
    curl \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# =====================================================
# STAGE 3: LANGUAGE RUNTIMES
# =====================================================
FROM builder AS runtime

# Python 3.11
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3-pip \
    && ln -sf /usr/bin/python3.11 /usr/bin/python3 \
    && rm -rf /var/lib/apt/lists/*

# Go 1.21.5
ENV GOLANG_VERSION=1.21.5
RUN wget -q https://go.dev/dl/go${GOLANG_VERSION}.linux-amd64.tar.gz \
    && tar -C /usr/local -xzf go${GOLANG_VERSION}.linux-amd64.tar.gz \
    && rm go${GOLANG_VERSION}.linux-amd64.tar.gz

ENV PATH="/usr/local/go/bin:${PATH}"

# Java
RUN apt-get update && apt-get install -y \
    default-jdk \
    && rm -rf /var/lib/apt/lists/*

# Node.js 20
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# TypeScript
RUN npm install -g typescript

# C/C++ libraries
RUN apt-get update && apt-get install -y \
    libstdc++-11-dev \
    && rm -rf /var/lib/apt/lists/*

# =====================================================
# STAGE 4: ISOLATE INSTALLATION
# =====================================================
FROM runtime AS isolate-builder

WORKDIR /tmp
RUN git clone https://github.com/ioi/isolate.git \
    && cd isolate \
    && make isolate \
    && make install \
    && cd .. \
    && rm -rf isolate

# Isolate directories with proper permissions
RUN mkdir -p /var/local/lib/isolate \
    && chmod 777 /var/local/lib/isolate

# MUHIM: Isolate config (agar kerak bo'lsa)
RUN mkdir -p /etc/isolate \
    && echo "box_root = /var/local/lib/isolate" > /etc/isolate.conf

# =====================================================
# STAGE 5: FINAL IMAGE
# =====================================================
FROM isolate-builder AS final

WORKDIR /app

# Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Application code
COPY . .

# Expose port
EXPOSE 8080

# CRITICAL: Use tmpfs for isolate (fixes "Unexpected mountpoint")
VOLUME /var/local/lib/isolate

# Entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["python3", "app/main.py"]