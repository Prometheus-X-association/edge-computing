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

NAME := controller
VERSION := 1.0
IMG := ptx-edge/${NAME}:${VERSION}

build:
	docker build -t ${IMG} .
	docker images --no-trunc ${IMG}

run: build
	docker run --rm --name ${NAME} -ti ${IMG}

clean:
	docker rmi -f ${IMG}
	py3clean -v .
	rm -rf .venv

########################################################################################################################

docker-test-setup: build

docker-unit-tests: docker-test-setup
	@echo ">>> No unit test is defined for controller!"

unit-tests:
	@echo ">>> No unit test is defined for controller!"

.PHONY: *
.DEFAULT_GOAL := build