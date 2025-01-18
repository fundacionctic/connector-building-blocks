FROM ubuntu:20.04

RUN apt-get update -y && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    curl \
    iputils-ping \
    openjdk-17-jdk \
    git \
    unzip \
    zip \
    wget \
    avahi-utils \
    python3 \
    python3-pip

ENV GRADLE_VERSION=8.11

RUN wget --quiet -O gradle-${GRADLE_VERSION}-bin.zip https://services.gradle.org/distributions/gradle-${GRADLE_VERSION}-bin.zip && \
    unzip -d /opt/gradle gradle-${GRADLE_VERSION}-bin.zip && \
    ln -s /opt/gradle/gradle-${GRADLE_VERSION} /opt/gradle/latest && \
    echo 'export GRADLE_HOME=/opt/gradle/latest' | tee /etc/profile.d/gradle.sh && \
    echo 'export PATH=$PATH:$GRADLE_HOME/bin' | tee -a /etc/profile.d/gradle.sh && \
    chmod +x /etc/profile.d/gradle.sh

ENV PATH_EDCPY=/opt/edcpy
ENV POETRY_VERSION=1.8.4

RUN mkdir -p ${PATH_EDCPY}
WORKDIR ${PATH_EDCPY}

COPY ./edcpy .
RUN pip install poetry==${POETRY_VERSION}
RUN /usr/local/bin/poetry install
RUN /usr/local/bin/poetry build
RUN pip install -U dist/*.whl

ENV PATH_CONNECTOR=/opt/connector

RUN mkdir -p ${PATH_CONNECTOR}
WORKDIR ${PATH_CONNECTOR}

ARG ENABLE_OAUTH2=false
ARG ENABLE_SSI=false
ARG DISABLE_AUTH=false
ARG ENABLE_FEDERATED_CATALOG=false

COPY ./connector .

ENV ORG_GRADLE_PROJECT_useOauthIdentity=${ENABLE_OAUTH2}
ENV ORG_GRADLE_PROJECT_useSSI=${ENABLE_SSI}
ENV ORG_GRADLE_PROJECT_disableAuth=${DISABLE_AUTH}
ENV ORG_GRADLE_PROJECT_enableFederatedCatalog=${ENABLE_FEDERATED_CATALOG}

RUN /opt/gradle/latest/bin/gradle clean build

COPY ./scripts/generate-vault.sh .
COPY ./run-connector.sh .

CMD [ "/opt/connector/run-connector.sh" ]
