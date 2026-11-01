BORGMATIC_IMAGE_VERSION ?= latest
INTEGRATION_IMAGE ?= borgmatic-exporter:integration
INTEGRATION_BACKEND ?= docker

.PHONY: dev test integration-test integration-image format lint

dev:
	@poetry lock --verbose
	@poetry install --all-extras --verbose
	@poetry export -f requirements.txt --output requirements.txt --without dev --without-hashes
	@poetry show

test:
	@poetry run pytest --cov-config=pyproject.toml --cov-report=term --cov src
	@poetry run coverage html

format:
	@poetry run black .
	@poetry run isort .

lint:
	@poetry run pylint src

# Native mode needs Borg and borgmatic on PATH; Docker mode tests the release image.
integration-test:
ifeq ($(INTEGRATION_BACKEND),docker)
	@$(MAKE) integration-image
endif
	@poetry run pytest -m integration --integration-backend=$(INTEGRATION_BACKEND) --integration-image=$(INTEGRATION_IMAGE) --junitxml=.integration-artifacts/results.xml tests/integration

integration-image:
	@docker build --build-arg BORGMATIC_IMAGE_VERSION=$(BORGMATIC_IMAGE_VERSION) -t $(INTEGRATION_IMAGE) .
