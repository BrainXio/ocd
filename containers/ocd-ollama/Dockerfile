# Build: docker build -t ocd-ollama:latest containers/ocd-ollama/

ARG BASE_IMAGE=ocd-base
ARG BASE_TAG=latest
ARG OLLAMA_VERSION=0.21.0

FROM ${BASE_IMAGE}:${BASE_TAG}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

LABEL org.opencontainers.image.source=https://github.com/BrainXio/ocd
LABEL org.opencontainers.image.description="Ollama runtime image for local LLM inference in the OCD project"
LABEL org.opencontainers.image.licenses=MIT

ARG OLLAMA_VERSION

USER root

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        ca-certificates \
        curl \
        zstd \
    && mkdir -p /tmp/ollama-install \
    && curl --retry 6 --retry-delay 10 -fsSL "https://github.com/ollama/ollama/releases/download/v${OLLAMA_VERSION}/ollama-linux-amd64.tar.zst" \
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