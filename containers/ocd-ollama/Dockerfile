# Build: docker build --build-arg BASE_TAG=0.1.0 -t ocd-ollama:0.1.0 containers/ocd-ollama/

ARG BASE_IMAGE=ocd-base
ARG BASE_TAG=0.1.0
ARG OLLAMA_VERSION=0.21.0

FROM ${BASE_IMAGE}:${BASE_TAG}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ARG OLLAMA_VERSION

USER root

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        ca-certificates \
        curl \
        zstd \
    && mkdir -p /tmp/ollama-install \
    && curl -fsSL "https://github.com/ollama/ollama/releases/download/v${OLLAMA_VERSION}/ollama-linux-amd64.tar.zst" \
        | zstd -d \
        | tar -xC /tmp/ollama-install \
    && mv /tmp/ollama-install/bin/ollama /usr/local/bin/ollama \
    && chmod +x /usr/local/bin/ollama \
    && rm -rf /tmp/ollama-install \
    && apt-get purge -y curl zstd \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

USER ocd

ENV OLLAMA_HOST=0.0.0.0

# Create data directory for model storage
RUN mkdir -p /home/ocd/.ollama

VOLUME /home/ocd/.ollama

EXPOSE 11434

HEALTHCHECK NONE

CMD ["ollama", "serve"]