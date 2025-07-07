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
SAMPLES_PREFIX := samples
CONVNET_IMG := ${SAMPLES_PREFIX}/convnet-worker:0.1
GBC_IMG := ${SAMPLES_PREFIX}/gbc-worker:0.1

# Docker commands
build-convnet:
	docker build -t ${CONVNET_IMG} -f ./convnet/Dockerfile convnet/
	docker images --no-trunc ${CONVNET_IMG}

run-convnet: build-convnet
	docker run --rm --name convnet -ti ${CONVNET_IMG}

build-gbc:
	docker build -t ${GBC_IMG} -f ./gbc/Dockerfile gbc/
	docker images --no-trunc ${GBC_IMG}

run-gbc: build-gbc
	docker run --rm --name gbc -ti ${GBC_IMG}

build-all: build-convnet build-gbc

# Cleanup
clean:
	py3clean -v .

# Tests
docker-unit-tests docker-test-setup unit-tests:
	@echo "Skipped."

.PHONY: *