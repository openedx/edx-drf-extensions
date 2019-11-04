ROOT = $(shell echo "$$PWD")
COVERAGE = $(ROOT)/build/coverage
PACKAGE = edx_rest_framework_extensions

.PHONY: clean quality requirements _upgrade upgrade piptools test help

help: ## display this help message
	@echo "Please use \`make <target>' where <target> is one of"
	@grep '^[a-zA-Z]' $(MAKEFILE_LIST) | sort | awk -F ':.*?## ' 'NF==2 {printf "\033[36m  %-25s\033[0m %s\n", $$1, $$2}'

clean: ## remove intermediate files
	find . -name '*.pyc' -delete
	coverage erase
	rm -rf build

quality: ## run quality checks using tox
	tox -e quality

piptools:
	pip install -r pip-tools.txt

_upgrade: piptools
	# Generate pins for test requirements.
	pip-compile test_requirements.in --upgrade -o test_requirements.txt

	# Delete django pin from test_requirements.txt so that tox can control
	# Django version.
	sed '/^[dD]jango==/d' test_requirements.txt > test_requirements.tmp
	mv test_requirements.tmp test_requirements.txt

	# Delete line "-e file:///local/path/to/edx-drf-extensions", which
	# is a result of the "-e ." hack in test_requirements.in.
	sed '/^-e /d' test_requirements.txt > test_requirements.tmp
	mv test_requirements.tmp test_requirements.txt

	# Generate pins for pip-tools itself.
	pip-compile pip-tools.in --upgrade

upgrade: ## upgrade test requirement pins
	CUSTOM_COMPILE_COMMAND="make upgrade" make _upgrade

requirements: piptools ## install test requirements into current env
	pip-sync test_requirements.txt
	# `make upgrade` removes Django from test_requirements.txt,
	# so we manually install it here.
	pip install django~=1.11
	pip install -r docs/requirements.txt

test: ## run unit tests using tox
	tox
