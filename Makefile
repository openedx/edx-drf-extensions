ROOT = $(shell echo "$$PWD")
COVERAGE = $(ROOT)/build/coverage
PACKAGE = edx_rest_framework_extensions

clean:
	find . -name '*.pyc' -delete
	coverage erase
	rm -rf build

quality:
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

upgrade:
	CUSTOM_COMPILE_COMMAND="make upgrade" make _upgrade

requirements: piptools
	pip-sync test_requirements.txt
	# `make upgrade` removes Django from test_requirements.txt,
	# so we manually install it here.
	pip install django~=1.11  
	pip install -r docs/requirements.txt

test:
	tox

.PHONY: clean quality requirements _upgrade upgrade piptools
