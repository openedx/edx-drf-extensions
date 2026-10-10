ROOT = $(shell echo "$$PWD")
COVERAGE = $(ROOT)/build/coverage
PACKAGE = edx_rest_framework_extensions

.PHONY: clean help isort isort_check linting quality requirements \
        style test test-python upgrade

help: ## display this help message
	@echo "Please use \`make <target>' where <target> is one of"
	@grep '^[a-zA-Z]' $(MAKEFILE_LIST) | sort | awk -F ':.*?## ' 'NF==2 {printf "\033[36m  %-25s\033[0m %s\n", $$1, $$2}'

clean: ## remove intermediate files
	find . -name '*.pyc' -delete
	coverage erase
	rm -rf build

upgrade: ## update python dependencies
	uv run --with edx-lint edx_lint write_uv_constraints pyproject.toml
	uv lock --upgrade

requirements: ## install dev requirements into current env
	uv sync --locked --group dev

test: ## run unit tests in the current environment with coverage
	python -Wd -m pytest $(PYTEST_ARGS)
	coverage report

CHECK_DIRS=src/csrf src/edx_rest_framework_extensions

style: ## check that code is PEP-8 compliant.
	pycodestyle *.py $(CHECK_DIRS)

isort: ## sort imports
	isort $(CHECK_DIRS)

isort_check: ## check that imports are correctly sorted
	isort $(CHECK_DIRS) --check-only --diff

linting: ## check code quality with pylint
	pylint src/csrf
	# Disable "C" (convention) messages in `edx_rest_framework_extensions`
	# because there are so many violations (TODO: fix them).
	pylint --disable=C src/edx_rest_framework_extensions

quality: style isort_check linting ## run all code quality checks in current env
	@echo "Quality checking complete!"

test-python: ## run unit tests within this environment only
	python -Wd -m pytest
