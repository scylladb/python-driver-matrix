FROM python:3.10-slim-buster

# Debian Buster packages have moved from deb.debian.org to the archive.
RUN sed -i \
        -e 's@deb.debian.org/debian-security@archive.debian.org/debian-security@' \
        -e 's@deb.debian.org/debian@archive.debian.org/debian@' \
        -e '/buster-updates/d' /etc/apt/sources.list \
    && apt-get -o Acquire::Check-Valid-Until=false update \
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
    && rm -rf /var/lib/apt/lists/*

RUN apt-get -o Acquire::Check-Valid-Until=false -y update \
    && apt-get -y install openjdk-11-jdk-headless libev4 libev-dev liblz4-dev patch gcc git procps python2 docker-ce-cli \
    && pip install --upgrade pip \
    && rm -rf /var/lib/apt/lists/*

ADD requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

