# Build: docker build -t ocd-python:latest containers/ocd-python/

ARG BASE_IMAGE=ocd-base
ARG BASE_TAG=latest

FROM ${BASE_IMAGE}:${BASE_TAG}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

LABEL org.opencontainers.image.source=https://github.com/BrainXio/ocd
LABEL org.opencontainers.image.description="Python 3.12+ toolchain image with ruff, mypy, and mdformat for the OCD project"

ARG PYTHON_VERSION=3.12

ENV PATH="/home/ocd/.local/bin:${PATH}"

# Install Python and linters as ocd user
RUN uv python install "${PYTHON_VERSION}" \
    && uv tool install ruff \
    && uv tool install mypy \
    && uv tool install mdformat --with mdformat-frontmatter

# Symlink python3 to a system path so it is on PATH for all users
USER root
RUN PYTHON_BIN="$(find /home/ocd/.local/share/uv/python -name python3 -path "*/cpython-${PYTHON_VERSION}*/bin/python3" | head -1)" \
    && ln -sf "${PYTHON_BIN}" /usr/local/bin/python3 \
    && ln -sf "${PYTHON_BIN}" /usr/local/bin/python
USER ocd

HEALTHCHECK NONE

CMD ["python3"]