FROM python:3.10-bullseye
WORKDIR /root
RUN apt-get update -y && apt-get install -y openssh-client openssl
COPY . .
RUN pip install -r requirements.txt