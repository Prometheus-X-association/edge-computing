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

# Docker commands
build:
	docker build -t ${IMG} .
	docker images --no-trunc ${IMG}

run:
	docker run --rm --name ${NAME} -ti -p 8080:8080 ${IMG}

# Local development in venv
venv:
	test -d .venv || (\
		python3 -m venv --upgrade-deps .venv && \
		. .venv/bin/activate && \
		python3 -m pip install -U -r requirements.txt -r test-requirements.txt \
		)

# Cleanup
clean:
	docker rmi -f ${IMG}
	py3clean -v .
	rm -rf .venv

# Tests
unit-tests: venv
	( . .venv/bin/activate && tox )

docker-test-setup: build
	docker build -t ${TEST_IMG} -f test.Dockerfile .
	docker images --no-trunc ${TEST_IMG}

docker-unit-tests: docker-test-setup
ifdef REPORT_PATH
	docker run --rm --mount="type=bind,src=${REPORT_PATH},dst=/usr/src/app/report/" -ti ${TEST_IMG}
else
	docker run --rm -ti ${TEST_IMG}
endif

.PHONY: build venv unit-tests docker-test-setup docker-unit-tests
.DEFAULT_GOAL := unit-tests