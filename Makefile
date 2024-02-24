dev:
	@poetry lock --verbose --no-update
	@poetry install --all-extras --verbose
	@poetry show

test:
	@poetry run pytest --cov-config=pyproject.toml --cov-report=term --cov src
	@poetry run coverage html

format:
	@poetry run black .
	@poetry run isort .

lint:
	@poetry run pylint src
