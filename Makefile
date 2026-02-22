# backend/Makefile — Build & push to GHCR

REGISTRY ?= ghcr.io/darkestabed
IMAGE    ?= fridai-backend
TAG      ?= latest

FULL_IMAGE = $(REGISTRY)/$(IMAGE):$(TAG)

.PHONY: build push login test

build:
	docker build -t $(FULL_IMAGE) .

push: build
	docker push $(FULL_IMAGE)

login:
	@echo "Paste a GitHub PAT with write:packages scope"
	@docker login ghcr.io -u <OWNER>

test:
	docker run --rm $(FULL_IMAGE) pytest -q
