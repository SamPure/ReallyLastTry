#!/usr/bin/env bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Running pre-commit hooks...${NC}"
pre-commit run --all-files

echo -e "\n${YELLOW}Running type checking...${NC}"
mypy app

echo -e "\n${YELLOW}Running linting...${NC}"
flake8 app tests
black --check app tests
isort --check-only app tests

echo -e "\n${YELLOW}Running security checks...${NC}"
bandit -r app/
safety check

echo -e "\n${YELLOW}Running tests...${NC}"
# Run unit tests first
echo -e "${YELLOW}Running unit tests...${NC}"
pytest -m "unit" --cov=app --cov-report=term-missing

# Run integration tests if not in CI
if [ -z "$CI" ]; then
    echo -e "\n${YELLOW}Running integration tests...${NC}"
    pytest -m "integration" --cov=app --cov-report=term-missing
fi

# Run performance tests if not in CI
if [ -z "$CI" ]; then
    echo -e "\n${YELLOW}Running performance tests...${NC}"
    pytest -m "performance" --cov=app --cov-report=term-missing
fi

echo -e "\n${GREEN}All checks passed!${NC}"
