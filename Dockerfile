FROM ubuntu:20.04

RUN apt-get update -y && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    curl \
    iputils-ping \
    openjdk-17-jdk \
    git \
    unzip \
    zip \
    wget \
    avahi-utils

RUN sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b /usr/local/bin

ENV GRADLE_VERSION=8.1.1

RUN wget --quiet -O gradle-${GRADLE_VERSION}-bin.zip https://services.gradle.org/distributions/gradle-${GRADLE_VERSION}-bin.zip && \
    unzip -d /opt/gradle gradle-${GRADLE_VERSION}-bin.zip && \
    ln -s /opt/gradle/gradle-${GRADLE_VERSION} /opt/gradle/latest && \
    echo 'export GRADLE_HOME=/opt/gradle/latest' | tee /etc/profile.d/gradle.sh && \
    echo 'export PATH=$PATH:$GRADLE_HOME/bin' | tee -a /etc/profile.d/gradle.sh && \
    chmod +x /etc/profile.d/gradle.sh

ENV PATH_APP=/opt/connector

RUN mkdir -p ${PATH_APP}
WORKDIR ${PATH_APP}

ARG ENABLE_OAUTH2=true

COPY ./connector .
ENV ORG_GRADLE_PROJECT_useOauthIdentity=${ENABLE_OAUTH2}
RUN /opt/gradle/latest/bin/gradle clean build

COPY ./scripts/keystore-to-vault.sh .

CMD ${PATH_APP}/keystore-to-vault.sh && \
    java \
    -Dedc.fs.config=${PROPERTIES_FILE_PATH} \
    -Dedc.vault=${PATH_APP}/vault.properties \
    -Dedc.keystore=${KEYSTORE_PATH} \
    -Dedc.keystore.password=${KEYSTORE_PASSWORD} \
    -jar ${PATH_APP}/core-connector/build/libs/core-connector.jar