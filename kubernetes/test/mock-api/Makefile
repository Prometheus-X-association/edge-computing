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

NAME := rest-api
VERSION := 0.1
IMG := ptx-edge/${NAME}:${VERSION}
TEST_IMG := ptx-edge/${NAME}-test:${VERSION}
PY := python3.12

# Docker commands
build:
	docker build -t ${IMG} .
	docker images --no-trunc ${IMG}

run: build
	docker run --rm --name ${NAME} -ti -p 8080:8080 ${IMG}

dev:
	docker run --rm --name ${NAME} -ti -p 8080:8080 -v ./app:/usr/src/api/app ${IMG} \
				uvicorn app.main:app --port 8080 --reload --reload-dir app


# Local development in venv
venv:
	test -d .venv || (\
		${PY} -m venv --upgrade-deps .venv && \
		. .venv/bin/activate && \
		${PY} -m pip install -U -r requirements.txt -r requirements-dev.txt \
		)

dev-local: venv
		(\
		. .venv/bin/activate && \
		fastapi dev --port 8080 --reload app/main.py \
		)

setup:
ifeq ($(shell [ `command -v ${PY} >/dev/null 2>&1` -a `command -v pip3.13 >/dev/null 2>&1` ] || echo 1), 1)
	$(error "Missing required environment: ${PY} + pip")
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
	docker build -t ${TEST_IMG} -f test.Dockerfile --build-arg USER=$$(id -u)  .
	docker images --no-trunc ${TEST_IMG}

docker-unit-tests: docker-test-setup
ifdef REPORT_PATH
	docker run --rm --mount="type=bind,src=${REPORT_PATH},dst=/usr/src/api/report/" -ti ${TEST_IMG}
else
	docker run --rm -ti ${TEST_IMG}
endif

.PHONY: build run dev venv dev-local setup clean tests unit-tests docker-test-setup docker-unit-tests
.DEFAULT_GOAL := dev