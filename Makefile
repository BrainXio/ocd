REGISTRY := ghcr.io/brainxio
TAG := latest
GPU_FLAG := $(shell docker info 2>/dev/null | grep -q 'nvidia' && echo '--gpus=all' || true)

# Short tags for Dockerfile FROM resolution, GHCR tags for devcontainer compatibility.
# Docker prefers local images over registry pulls, so devcontainer.json works locally
# without pushing anything.
# GPU_FLAG is set to --gpus=all when an NVIDIA runtime is available (harmless no-op otherwise).

.PHONY: all base python node ollama ocd test clean

all: ocd

base:
	docker build -t ocd-base:$(TAG) -t $(REGISTRY)/ocd-base:$(TAG) containers/ocd-base/

python: base
	docker build --build-arg BASE_TAG=$(TAG) \
		-t ocd-python:$(TAG) -t $(REGISTRY)/ocd-python:$(TAG) \
		containers/ocd-python/

node: base
	docker build --build-arg BASE_TAG=$(TAG) \
		-t ocd-node:$(TAG) -t $(REGISTRY)/ocd-node:$(TAG) \
		containers/ocd-node/

ollama: base
	docker build --build-arg BASE_TAG=$(TAG) \
		-t ocd-ollama:$(TAG) -t $(REGISTRY)/ocd-ollama:$(TAG) \
		containers/ocd-ollama/

ocd: python
	docker build --build-arg BASE_TAG=$(TAG) \
		-t ocd:$(TAG) -t $(REGISTRY)/ocd:$(TAG) \
		-f containers/ocd/Dockerfile .

test: ocd
	@echo "=== Smoke testing ocd:$(TAG) ==="
	docker run --rm $(GPU_FLAG) --entrypoint="" ocd:$(TAG) python3 --version
	docker run --rm $(GPU_FLAG) --entrypoint="" ocd:$(TAG) node --version
	docker run --rm $(GPU_FLAG) --entrypoint="" ocd:$(TAG) ruff --version
	docker run --rm $(GPU_FLAG) --entrypoint="" ocd:$(TAG) which ocd
	docker run --rm $(GPU_FLAG) --entrypoint="" ocd:$(TAG) ls /home/ocd/.claude/
	docker run --rm $(GPU_FLAG) --entrypoint="" ocd:$(TAG) ls /opt/ocd/templates/
	@echo "=== GPU passthrough ==="
	@docker run --rm $(GPU_FLAG) --entrypoint="" ocd:$(TAG) nvidia-smi -L > /dev/null 2>&1 && \
		docker run --rm $(GPU_FLAG) --entrypoint="" ocd:$(TAG) nvidia-smi -L || \
		echo "  (no GPU detected — skipped)"
	@echo "=== All smoke tests passed ==="

clean:
	docker rmi \
		ocd:$(TAG) $(REGISTRY)/ocd:$(TAG) \
		ocd-python:$(TAG) $(REGISTRY)/ocd-python:$(TAG) \
		ocd-node:$(TAG) $(REGISTRY)/ocd-node:$(TAG) \
		ocd-ollama:$(TAG) $(REGISTRY)/ocd-ollama:$(TAG) \
		ocd-base:$(TAG) $(REGISTRY)/ocd-base:$(TAG) \
		2>/dev/null || true