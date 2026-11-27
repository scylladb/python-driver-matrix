FROM python:3.11-slim-bookworm

RUN apt-get update \
    && apt-get -y install \
                    ca-certificates \
                    curl \
                    gnupg \
                    lsb-release \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && echo \
       "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
       $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && curl -fsSL https://packages.adoptium.net/artifactory/api/gpg/key/public | gpg --dearmor -o /etc/apt/keyrings/adoptium.gpg \
    && echo \
       "deb [signed-by=/etc/apt/keyrings/adoptium.gpg] https://packages.adoptium.net/artifactory/deb \
       $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/adoptium.list > /dev/null \
    && rm -rf /var/lib/apt/lists/*

# Debian bookworm ships neither openjdk-11 nor python2; Java 11 comes from Adoptium (Temurin)
RUN apt-get -y update \
    && apt-get -y install temurin-11-jdk libev4 libev-dev liblz4-dev patch gcc git procps docker-ce-cli \
    && pip install --upgrade pip \
    && rm -rf /var/lib/apt/lists/*

ADD requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
