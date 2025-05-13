.PHONY: up down test lint clean

up:
	docker-compose up -d

down:
	docker-compose down

test:
	pytest --cov=app tests/

lint:
	black --check .
	flake8 .
	mypy app/

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
