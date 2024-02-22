#!/usr/bin/env bash

set -e
set -x

# Prerequisites
apt-get update -y
apt-get install -y curl iputils-ping openjdk-17-jdk git unzip zip python3-pip python3-virtualenv

# Docker
curl -fsSL https://get.docker.com -o install-docker.sh
sh install-docker.sh
usermod -aG docker vagrant

# Taskfile
sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b /usr/local/bin

# Gradle
wget --quiet -O gradle-8.6-bin.zip https://services.gradle.org/distributions/gradle-8.6-bin.zip
unzip -d /opt/gradle gradle-8.6-bin.zip
ln -s /opt/gradle/gradle-8.6 /opt/gradle/latest
echo 'export GRADLE_HOME=/opt/gradle/latest' | tee /etc/profile.d/gradle.sh
echo 'export PATH=$PATH:$GRADLE_HOME/bin' | tee -a /etc/profile.d/gradle.sh
chmod +x /etc/profile.d/gradle.sh

# Check the versions to make sure everything is installed correctly
docker info
java --version
task --version
