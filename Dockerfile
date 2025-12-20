# ==============================
# Base image
# ==============================
FROM ubuntu:22.04

# ==============================
# Environment vars
# ==============================
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

# ==============================
# Install dependencies
# ==============================
RUN apt update && apt install -y \
    python3 python3-pip \
    g++ gcc \
    openjdk-17-jdk \
    golang-go \
    sudo wget vim curl gnupg2 unzip \
    build-essential \
    && apt clean \
    && rm -rf /var/lib/apt/lists/*

# ==============================
# NodeJS & TypeScript
# ==============================
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt install -y nodejs \
    && npm install -g typescript \
    && npm install -g npm

# ==============================
# Install Isolate
# ==============================
RUN wget http://archive.ubuntu.com/ubuntu/pool/universe/i/isolate/isolate_2.2.1-2_amd64.deb \
    && dpkg -i isolate_2.2.1-2_amd64.deb || apt-get install -f -y \
    && rm isolate_2.2.1-2_amd64.deb

# ==============================
# Setup working directory
# ==============================
WORKDIR /app

# ==============================
# Copy project files
# ==============================
COPY . /app

# ==============================
# Install Python requirements
# ==============================
RUN pip3 install --no-cache-dir -r requirements.txt

# ==============================
# Expose port (agar Flask ishlatilsa)
# ==============================
EXPOSE 5000

# ==============================
# Default command
# ==============================
CMD ["python3", "app.py"]
