# Build: docker build -t ocd:latest -f containers/ocd/Dockerfile .

ARG BASE_IMAGE=ocd-python
ARG BASE_TAG=latest
ARG OLLAMA_VERSION=0.21.0

FROM ${BASE_IMAGE}:${BASE_TAG}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

LABEL org.opencontainers.image.source=https://github.com/BrainXio/ocd
LABEL org.opencontainers.image.description="OCD product image with Python, Node.js, Ollama, Claude Code, and the OCD package"
LABEL org.opencontainers.image.licenses=MIT

ARG OLLAMA_VERSION

USER root

# Install Node.js 22 toolchain (same as ocd-node)
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        ca-certificates \
        curl \
    && curl --retry 6 --retry-delay 10 -fsSL https://deb.nodesource.com/setup_22.x | bash - \
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

# Install Ollama
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

# Install Claude Code (native installer)
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        ca-certificates \
        curl \
    && curl --retry 6 --retry-delay 10 -fsSL https://claude.ai/install.sh | bash \
    && cp -L /root/.local/bin/claude /usr/local/bin/claude \
    && chmod +x /usr/local/bin/claude \
    && apt-get purge -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# ── OCD Package ──────────────────────────────────────────────────────
# Dedicated venv at /opt/ocd/venv/ survives the workspace mount.
# PATH puts OCD entry points before the project venv.
COPY pyproject.toml uv.lock /tmp/ocd-build/
COPY src/ocd/ /tmp/ocd-build/src/ocd/
COPY .claude/ /tmp/ocd-source/.claude/
RUN python /tmp/ocd-build/src/ocd/pack.py \
        --source /tmp/ocd-source/.claude \
        --output /tmp/ocd-build/src/ocd/data/content.db \
    && uv venv /opt/ocd/venv \
    && uv pip install --python /opt/ocd/venv/bin/python /tmp/ocd-build \
    && rm -rf /tmp/ocd-build /tmp/ocd-source

# ── User-level Claude Code config ───────────────────────────────────
# Skills, agents, rules, and settings at ~/.claude/ are available
# to all projects immediately (no ocd init needed for these).
COPY .claude/ /home/ocd/.claude/
RUN rm -f /home/ocd/.claude/settings.local.json \
    && chown -R ocd:ocd /home/ocd/.claude

# ── OCD Templates ──────────────────────────────────────────────────
# Project-level files that ocd init copies to the workspace.
# These must be at the project root (not user-level) to work correctly.
COPY .githooks/ /opt/ocd/templates/.githooks/
COPY .gitleaks.toml /opt/ocd/templates/.gitleaks.toml
COPY package.json package-lock.json /opt/ocd/templates/

# ── Dependency Cache ────────────────────────────────────────────────
# Dependency specs only (cached unless deps change).
# Project NOT installed yet — done by ocd init.
COPY pyproject.toml uv.lock package.json package-lock.json /home/ocd/project/
RUN chown -R ocd:ocd /home/ocd/project

USER ocd
WORKDIR /home/ocd/project

# Install Python and Node dependencies (project NOT installed yet — done by ocd init)
RUN uv sync --no-install-project && npm ci

ENV OLLAMA_HOST=0.0.0.0
# OCD venv takes precedence over project venv for entry points.
# Project venv is still on PATH for project-installed tools.
ENV PATH="/opt/ocd/venv/bin:/home/ocd/project/.venv/bin:/home/ocd/.local/bin:${PATH}"

HEALTHCHECK NONE

ENTRYPOINT ["ocd"]
CMD ["init"]