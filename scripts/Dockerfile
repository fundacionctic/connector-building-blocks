FROM python:3.10-bullseye

RUN apt-get update -y && apt-get install -y \
    openssh-client \
    openssl \
    iputils-ping

WORKDIR /root
COPY . .
