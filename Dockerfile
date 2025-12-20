# Base image
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

# Update & install dependencies including isolate
RUN apt update && \
    apt install -y software-properties-common && \
    add-apt-repository universe && \
    apt update && \
    apt install -y \
        isolate \
        python3 python3-pip \
        g++ gcc \
        openjdk-17-jdk \
        golang-go \
        sudo wget vim curl unzip \
        build-essential \
    && apt clean && rm -rf /var/lib/apt/lists/*

# NodeJS & TypeScript
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt install -y nodejs \
    && npm install -g typescript npm

# Set working directory
WORKDIR /app

# Copy project
COPY . /app

# Python requirements
RUN pip3 install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 5000

# Default command
CMD ["python3", "app.py"]
