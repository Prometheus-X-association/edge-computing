# Tests

# Local development in venv
venv:
	test -d .venv || (\
		python3 -m venv --upgrade-deps .venv && \
		. .venv/bin/activate && \
		python3 -m pip install -U -r requirements.txt -r test-requirements.txt \
		)

unit-tests: venv
	( . .venv/bin/activate && tox )

.PHONY: unit-tests
.DEFAULT_GOAL := unit-tests