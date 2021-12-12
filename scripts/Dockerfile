FROM python:3.8-slim-buster

RUN apt-get -y update \
    && apt-get -y install software-properties-common \
    && apt-add-repository 'deb http://security.debian.org/debian-security stretch/updates main' \
    && apt-get -y update \
    && apt-get -y install openjdk-8-jdk-headless libev4 libev-dev patch gcc git procps \
    && pip install --upgrade pip \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /root/.cache/pip

ADD requirements.txt requirements.txt
RUN pip install -r requirements.txt

