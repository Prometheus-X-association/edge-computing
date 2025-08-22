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
SHELL := '/bin/bash'
.SHELLFLAGS = '-exc'

PTX_PREFIX := ptx
PTX_SANDBOX_PREFIX := ptx-sandbox
PTX_CORE := catalog contract consent
PDC_REPO := https://github.com/Prometheus-X-association/dataspace-connector.git
PDC_VER := 1.9.5
PDC_ENV := production
MONGO_VER := 8.0.5

build-orig:
	TMP_DIR=$$(mktemp -d) && cd $${TMP_DIR}; \
	git clone ${PDC_REPO} && cd dataspace-connector; \
	git switch --detach v${PDC_VER}; \
	# docker compose build; \
	docker build -f ./docker/app/Dockerfile --build-arg ENV=${PDC_ENV} -t ${PTX_PREFIX}/connector:${PDC_VER} .; \
	# docker build -f ./docker/mongodb/Dockerfile -t ${PTX_PREFIX}/mongodb:${PDC_VER} .; \
	cd sandbox/infrastructure; \
	for bb in ${PTX_CORE}; do \
		docker build -f ./utils/$${bb}/Dockerfile -t ${PTX_SANDBOX_PREFIX}/$${bb}:${PDC_VER} .; \
	done; \
	rm -rf $${TMP_DIR}
	docker images -f reference=${PTX_PREFIX}/* -f reference=${PTX_SANDBOX_PREFIX}/*

build-pdc:
	TMP_DIR=$$(mktemp -d) && pushd $${TMP_DIR}; \
		git clone ${PDC_REPO} && cd dataspace-connector; \
		git switch --detach v${PDC_VER}; \
	popd; \
	cp -v ./pdc/.dockerignore $${TMP_DIR}/dataspace-connector; \
	docker build -f ./pdc/connector.Dockerfile --build-arg ENV=${PDC_ENV} \
					-t ${PTX_PREFIX}/connector:${PDC_VER}-slim $${TMP_DIR}/dataspace-connector; \
	docker build -f ./pdc/mongodb.Dockerfile --build-arg MONGO_VER=${MONGO_VER} \
					-t ${PTX_PREFIX}/mongodb:${MONGO_VER}-slim $${TMP_DIR}/dataspace-connector; \
	rm -rf $${TMP_DIR}

build:
	TMP_DIR=$$(mktemp -d) && pushd $${TMP_DIR}; \
		git clone ${PDC_REPO} && cd dataspace-connector; \
		git switch --detach v${PDC_VER}; \
	popd; \
	cp -v ./pdc/.dockerignore $${TMP_DIR}/dataspace-connector; \
	docker build -f ./pdc/connector.Dockerfile --build-arg ENV=${PDC_ENV} \
					-t ${PTX_PREFIX}/connector:${PDC_VER}-slim $${TMP_DIR}/dataspace-connector; \
	docker build -f ./pdc/mongodb.Dockerfile --build-arg MONGO_VER=${MONGO_VER} \
					-t ${PTX_PREFIX}/mongodb:${MONGO_VER}-slim $${TMP_DIR}/dataspace-connector; \
	# cd sandbox/infrastructure; \
	docker build -f ./sandbox/mongoseed.Dockerfile -t ${PTX_SANDBOX_PREFIX}/mongo-seed:${PDC_VER}-slim \
					$${TMP_DIR}/dataspace-connector/sandbox/infrastructure/utils/connector/mongo-seed/; \
	for bb in ${PTX_CORE}; do \
		docker build -f ./sandbox/$${bb}.Dockerfile -t ${PTX_SANDBOX_PREFIX}/$${bb}:${PDC_VER}-slim \
							$${TMP_DIR}/dataspace-connector/sandbox/infrastructure/; \
	done; \
	rm -rf $${TMP_DIR}
	docker images --no-trunc -f reference=${PTX_PREFIX}/* -f reference=${PTX_SANDBOX_PREFIX}/*

########################################################################################################################

run-catalog:
	@# cd pdc && docker compose up catalog
	docker ps -aq -f name=ptx-catalog | xargs -r docker rm -f
	docker run -d --name ptx-catalog -p 3002:8082 --no-healthcheck \
					--add-host gw.ptx-edge.cluster.k3s:host-gateway -ti ptx-sandbox/catalog:${PDC_VER}-slim
	docker ps -f name=ptx-catalog

run-pdc:
	cd pdc && docker compose up

stop-pdc:
	cd pdc && docker compose down -v

run-pdc-test:
	cd pdc && docker compose -f test/docker-compose.yaml up

stop-pdc-test:
	cd pdc && docker compose -f test/docker-compose.yaml down -v

########################################################################################################################

run-core:
	cd sandbox && docker compose up

stop-core:
	cd sandbox && docker compose down -v

run-sandbox:
	cd sandbox && docker compose --profile mocked up

stop-sandbox:
	cd sandbox && docker compose --profile mocked down -v
	rm -f .pdc.login.json

########################################################################################################################

docker-test-setup: build

docker-unit-tests: docker-test-setup
	cd sandbox && docker compose up --force-recreate --always-recreate-deps --wait --wait-timeout=60
	curl -SsLI -o /dev/null http://localhost:3002/v1/catalog/participants/66d18a1dee71f9f096baec08
	@echo ">>> No unit test is defined for PTX sandbox!"
	cd sandbox && docker compose down --timeout=30

unit-tests:
	@echo ">>> No local unit test is defined for PTX sandbox!"

purge:
	docker image ls -q -f reference=${PTX_PREFIX}/* -f reference=${PTX_SANDBOX_PREFIX}/* | xargs -r docker rmi -f

.PHONY: build-orig build run-catalog run-pdc stop-pdc run-pdc-test stop-pdc-test run-core stop-core \
			run-sandbox stop-sandbox docker-test-setup docker-unit-tests unit-test purge
.DEFAULT_GOAL := build
