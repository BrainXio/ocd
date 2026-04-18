# Build: docker build -t ocd-node:latest containers/ocd-node/

ARG BASE_IMAGE=ocd-base
ARG BASE_TAG=latest

FROM ${BASE_IMAGE}:${BASE_TAG}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

USER root

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        ca-certificates \
        curl \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install --no-install-recommends -y \
        nodejs \
    && corepack enable \
    && corepack prepare pnpm@latest --activate \
    && npm install --global \
        prettier@3 \
        eslint@9 \
        stylelint@16 \
        htmlhint@1 \
    && apt-get purge -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

USER ocd

HEALTHCHECK NONE

CMD ["node"]