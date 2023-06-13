#!/usr/bin/env bash

set -e
set -x

apt-get update -y
apt-get install -y curl iputils-ping openjdk-17-jdk git unzip zip
curl -fsSL https://get.docker.com -o install-docker.sh
sh install-docker.sh
usermod -aG docker vagrant
sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b /usr/local/bin
wget -q https://gradle.org/next-steps/?version=8.1.1&format=bin -P /tmp
sudo unzip -q -d /opt/gradle /tmp/gradle-8.1.1-bin.zip
echo 'export PATH=$PATH:/opt/gradle/gradle-8.1.1/bin' >> ~/.bashrc
source ~/.bashrc

docker info
java --version
task --version
gradle --version