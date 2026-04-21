---
name: docker
description: Docker build, run, debug, and optimize commands. Use when the user asks to build, test, inspect, or troubleshoot Docker images and containers, or when working with Dockerfiles or docker-compose files.
argument-hint: '[build|run|test|logs|shell|clean] [image:tag]'
---

# Docker Skill

You are a Docker expert. When invoked, perform the requested Docker operation following these practices.

## Commands

The first argument determines the action:

### `/docker build [image:tag]`

Build the Docker image from the project's Dockerfile:

```bash
docker build -t ${1:-<project>:latest} .
```

- Use `--no-cache` only if the user requests a clean build
- Always use `--progress=plain` for visible output in CI
- Check for `.dockerignore` and warn about large excluded paths

### `/docker run [image:tag]`

Run the container with appropriate flags based on the project's requirements:

- Map ports explicitly based on what the container exposes
- Use `--rm` for ephemeral test runs
- Add any required capabilities (e.g., `--cap-add=NET_ADMIN` for containers with firewall rules)
- Mount named volumes for persistent data paths

### `/docker test [image:tag]`

Full validation pipeline:

1. Build the image
1. Run with required capabilities
1. Wait for startup, check logs for expected markers
1. Verify services are responsive (health checks)
1. Verify security constraints are applied (e.g., firewall rules, user permissions)
1. Verify no dev-only tools leaked into the final image
1. Clean up with `docker rm -f`

### `/docker logs [container]`

Show container logs, filtering for relevant output:

```bash
docker logs ${1:-<container>} 2>&1 | grep -E '<marker>|error|Error|FAILED|Warning'
```

Use markers specific to the project's logging format.

### `/docker shell [container]`

Open an interactive shell in the running container:

```bash
docker exec -it ${1:-<container>} bash
```

Use the container's default shell (bash, zsh, sh as appropriate).

### `/docker clean`

Remove project-related containers and images:

```bash
docker rm -f <project> <project>-test 2>/dev/null
docker rmi <project>:test <project>:latest 2>/dev/null
docker volume prune -f
```

## Best Practices

- Always tag builds with meaningful names (`<project>:test` for testing, `<project>:latest` for production)
- Use `docker buildx` for multi-platform builds when targeting registries
- Lint all shell scripts before building
- Never use `--no-cache` unless explicitly asked
- Use `docker compose` when the project has a compose file; otherwise prefer direct `docker` commands
- After building, always run a quick smoke test before declaring success
- When debugging, check logs first with `docker logs`, then `docker exec` for deeper inspection

## Image Optimization

When reviewing or modifying Dockerfiles:

- Minimize layers by combining related RUN commands
- Use `--no-install-recommends` with apt-get
- Clean up apt lists in the same layer: `rm -rf /var/lib/apt/lists/*`
- Order layers from least to most frequently changing
- Use multi-stage builds only when they genuinely reduce image size
- Always use `SHELL ["/bin/bash", "-o", "pipefail", "-c"]` for safe piped commands
