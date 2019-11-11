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
	pip install -r requirements/pip-tools.txt

_upgrade: piptools
	pip-compile requirements/base.in --rebuild --upgrade -o requirements/base.txt
	pip-compile requirements/test.in --rebuild --upgrade -o requirements/test.txt
	pip-compile requirements/docs.in --rebuild --upgrade -o requirements/docs.txt
	pip-compile requirements/dev.in --rebuild --upgrade -o requirements/dev.txt
	
	# Delete django pin from test.txt so that tox can control
	# Django version.
	sed '/^[dD]jango==/d' requirements/test.txt > requirements/test.tmp
	mv requirements/test.tmp requirements/test.txt

	# Delete line "-e file:///local/path/to/edx-drf-extensions", which
	# is a result of the "-e ." hack in test.in.
	sed '/^-e /d' requirements/test.txt > requirements/test.tmp
	sed '/^-e /d' requirements/dev.txt > requirements/dev.tmp
	mv requirements/test.tmp requirements/test.txt
	mv requirements/dev.tmp requirements/dev.txt

	# Generate pins for pip-tools itself.
	pip-compile requirements/pip-tools.in --rebuild --upgrade -o requirements/pip-tools.txt

upgrade: ## upgrade test requirement pins
	CUSTOM_COMPILE_COMMAND="make upgrade" make _upgrade

requirements: piptools ## install dev requirements into current env
	pip-sync requirements/dev.txt

test: ## run unit tests using tox
	tox
