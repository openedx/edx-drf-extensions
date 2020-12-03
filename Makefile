ROOT = $(shell echo "$$PWD")
COVERAGE = $(ROOT)/build/coverage
PACKAGE = edx_rest_framework_extensions

.PHONY: clean help isort isort_check linting piptools quality requirements \
        style test upgrade upgrade upgrade-piptools

help: ## display this help message
	@echo "Please use \`make <target>' where <target> is one of"
	@grep '^[a-zA-Z]' $(MAKEFILE_LIST) | sort | awk -F ':.*?## ' 'NF==2 {printf "\033[36m  %-25s\033[0m %s\n", $$1, $$2}'

clean: ## remove intermediate files
	find . -name '*.pyc' -delete
	coverage erase
	rm -rf build

piptools: ## install pip-compile and pip-sync.
	pip install -qr requirements/pip.txt
	pip install -r requirements/pip-tools.txt

upgrade-piptools: piptools # upgrade pip-tools using pip-tools.
	pip-compile requirements/pip-tools.in --rebuild --upgrade -o requirements/pip-tools.txt

upgrade: export CUSTOM_COMPILE_COMMAND=make upgrade
upgrade: upgrade-piptools piptools ## upgrade requirement pins.
	pip-compile --allow-unsafe --rebuild -o requirements/pip.txt requirements/pip.in
	pip-compile requirements/base.in --upgrade -o requirements/base.txt
	pip-compile requirements/test.in --upgrade -o requirements/test.txt
	pip-compile requirements/docs.in --upgrade -o requirements/docs.txt
	pip-compile requirements/dev.in --upgrade -o requirements/dev.txt

	# Delete django, drf pins from test.txt so that tox can control
	# Django version.
	sed -i.tmp '/^[dD]jango==/d' requirements/test.txt
	sed -i.tmp '/^djangorestframework==/d' requirements/test.txt
	rm requirements/test.txt.tmp

requirements: piptools ## install dev requirements into current env
	pip-sync requirements/dev.txt

test: ## run unit tests in all supported environments using tox
	tox

CHECK_DIRS=csrf edx_rest_framework_extensions

style: ## check that code is PEP-8 compliant.
	pycodestyle *.py $(CHECK_DIRS)

isort: ## sort imports
	isort $(CHECK_DIRS) --recursive

isort_check: ## check that imports are correctly sorted
	isort $(CHECK_DIRS) --recursive  --check-only --diff

linting: ## check code quality with pylint
	pylint csrf
	# Disable "C" (convention) messages in `edx_rest_framework_extensions`
	# because there are so many violations (TODO: fix them).
	pylint --disable=C edx_rest_framework_extensions

quality: style isort_check linting ## run all code quality checks in current env
	@echo "Quality checking complete!"

test-python: ## run unit tests within this environment only
	python -Wd -m pytest
