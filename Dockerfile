FROM ubuntu:22.04

# Asosiy o'zgaruvchilar
ENV DEBIAN_FRONTEND=noninteractive
ENV GOLANG_VERSION=1.21.5
ENV PYTHON_VERSION=3.11
ENV JAVA_VERSION=17

# Tizimni yangilash va asosiy paketlarni o'rnatish
RUN apt-get update && apt-get install -y \
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
    software-properties-common \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Python o'rnatish
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3-pip \
    && ln -sf /usr/bin/python3.11 /usr/bin/python3 \
    && ln -sf /usr/bin/python3 /usr/bin/python \
    && rm -rf /var/lib/apt/lists/*

# Go o'rnatish
RUN wget https://go.dev/dl/go${GOLANG_VERSION}.linux-amd64.tar.gz \
    && tar -C /usr/local -xzf go${GOLANG_VERSION}.linux-amd64.tar.gz \
    && rm go${GOLANG_VERSION}.linux-amd64.tar.gz

ENV PATH="/usr/local/go/bin:${PATH}"
ENV GOPATH="/go"
ENV PATH="${GOPATH}/bin:${PATH}"

# C++ kompilyatori uchun kerakli kutubxonalar
RUN apt-get update && apt-get install -y \
    libstdc++-11-dev \
    && rm -rf /var/lib/apt/lists/*

# Isolate o'rnatish
WORKDIR /tmp
RUN git clone https://github.com/ioi/isolate.git \
    && cd isolate \
    && make isolate \
    && make install \
    && cd .. \
    && rm -rf isolate

# Isolate uchun kerakli kataloglarni yaratish
RUN mkdir -p /var/local/lib/isolate \
    && chmod 755 /var/local/lib/isolate

# Node.js va TypeScript o'rnatish (n-install orqali)
# Node.js va TypeScript o'rnatish (n-install orqali, alohida katalogga)
# Node.js va TypeScript o'rnatish (NodeSource orqali)
RUN curl -fsSL https://deb.nodesource.com/setup_24.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g typescript

# Java o'rnatish (OpenJDK)
RUN apt-get update && apt-get install -y openjdk-${JAVA_VERSION}-jdk \
    && rm -rf /var/lib/apt/lists/*

# Ishlash katalogi
WORKDIR /app

# Python dependencies
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# Loyihani konteynerga nusxalash
COPY . .

EXPOSE 8080

CMD ["bash"]
