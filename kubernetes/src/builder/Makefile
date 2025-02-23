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

# Docker commands
build:
	docker build -t ${IMG} .
	docker images --no-trunc ${IMG}

run:
	docker run --rm --name ${NAME} -ti  ${IMG}

dev:
	docker run --rm --name ${NAME} -ti -v ./app:/usr/src/builder/app ${IMG} \
				python3 app/builder.py

venv:
	test -d .venv || (\
		python3.13 -m venv --upgrade-deps .venv && \
		. .venv/bin/activate && \
		python3.13 -m pip install -U -r requirements.txt -r requirements-dev.txt \
		)

# Cleanup
clean:
	docker rmi -f ${IMG}
	py3clean -v .
	rm -rf .venv

# Tests
tests: venv
	( . .venv/bin/activate && pytest -v --suppress-no-test-exit-code )

unit-tests: venv
	( . .venv/bin/activate && tox )

.PHONY: build run dev venv dev-local openapi clean tests unit-tests
.DEFAULT_GOAL := dev
#.ONESHELL: dev-local openapi