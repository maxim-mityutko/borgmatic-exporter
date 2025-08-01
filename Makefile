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
