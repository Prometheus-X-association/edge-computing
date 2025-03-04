# Copyright 2025 Janos Czentye
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

NAME := builder
VERSION := 1.0
IMG := ptx-edge/${NAME}:${VERSION}
TEST_IMG := ptx-edge/${NAME}-test:${VERSION}

# Docker commands
build:
	docker build -t ${IMG} .
	docker images --no-trunc ${IMG}

run: build
	docker run --rm --name ${NAME} -ti ${IMG}

dev:
	docker run --rm --name ${NAME} -ti -v ./app:/usr/src/builder/app ${IMG} \
				python3.13 -m app.builder

venv:
	test -d .venv || (\
		python3.13 -m pip install -U virtualenv && \
		python3.13 -m venv --upgrade-deps .venv && \
		. .venv/bin/activate && \
		python3.13 -m pip install -U -r requirements.txt -r requirements-dev.txt \
		)

setup:
ifeq ($(shell [ `which python3.13` -a `which pip3.13` ] || echo 1), 1)
	$(error "Missing required environment: Python3.13 + pip")
else
	$(MAKE) venv
endif

# Cleanup
clean:
	docker rmi -f ${IMG}
	py3clean -v .
	rm -rf .venv

# Tests

tests: venv
	( . .venv/bin/activate && PYTHONPATH=. pytest -v --suppress-no-test-exit-code )

unit-tests: venv
	( . .venv/bin/activate && tox -v )

docker-test-setup: build
	docker build -t ${TEST_IMG} -f test.Dockerfile .
	docker images --no-trunc ${TEST_IMG}

docker-unit-tests: docker-test-setup
ifdef REPORT_PATH
	docker run --rm --mount="type=bind,src=${REPORT_PATH},dst=/usr/src/builder/report/" -ti ${TEST_IMG}
else
	docker run --rm -ti ${TEST_IMG}
endif

.PHONY: build run dev venv setup clean tests unit-tests docker-test-setup docker-unit-tests
.DEFAULT_GOAL := dev
#.ONESHELL: dev-local openapi