# Build: docker build -t ocd-base:latest containers/ocd-base/

FROM debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

LABEL org.opencontainers.image.source=https://github.com/BrainXio/ocd
LABEL org.opencontainers.image.description="Hardened Debian base image with uv, git, and shellcheck for the OCD project"
LABEL org.opencontainers.image.licenses=MIT

ARG UV_VERSION=0.11.7
ARG SHELLCHECK_VERSION=0.11.0

ENV DEBIAN_FRONTEND=noninteractive

# Install system packages, uv, and shellcheck in a single layer
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        ca-certificates \
        curl \
        git \
    && curl --retry 6 --retry-delay 10 -LsSf "https://astral.sh/uv/${UV_VERSION}/install.sh" | UV_INSTALL_DIR=/usr/local/bin sh \
    && curl --retry 6 --retry-delay 10 -LsSf "https://github.com/koalaman/shellcheck/releases/download/v${SHELLCHECK_VERSION}/shellcheck-v${SHELLCHECK_VERSION}.linux.x86_64.tar.gz" \
        | tar -xz --strip-components=1 -C /usr/local/bin "shellcheck-v${SHELLCHECK_VERSION}/shellcheck" \
    && apt-get purge -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with UID 1000 to match typical host user
ARG UID=1000
ARG GID=1000
RUN groupadd --gid "${GID}" ocd \
    && useradd --uid "${UID}" --gid ocd --create-home --shell /bin/bash ocd

USER ocd
WORKDIR /home/ocd

HEALTHCHECK NONE

CMD ["bash"]