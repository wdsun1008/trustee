.PHONY: install dev-install test lint format clean run

# Install production dependencies
install:
	pip install -e .

# Install development dependencies
dev-install:
	pip install -e ".[dev]"

# Run tests
test:
	pytest

# Run linting
lint:
	mypy src/
	black --check src/
	isort --check src/

# Format code
format:
	black src/
	isort src/

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

# Run the server
run:
	python -m trustee_mcp_server

# Build package
build:
	python -m build

# Help
help:
	@echo "Available targets:"
	@echo "  install     - Install production dependencies"
	@echo "  dev-install - Install development dependencies"
	@echo "  test        - Run tests"
	@echo "  lint        - Run linting checks"
	@echo "  format      - Format code"
	@echo "  clean       - Clean build artifacts"
	@echo "  run         - Run the MCP server"
	@echo "  build       - Build package"
	@echo "  help        - Show this help" 