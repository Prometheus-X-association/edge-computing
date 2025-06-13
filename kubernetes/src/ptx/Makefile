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
PDC_VER := 1.9.2
PDC_ENV := production
MONGO_VER := 8.0.5

build-orig:
	(\
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
		rm -rf $${TMP_DIR}; \
	)
	docker images -f reference=${PTX_PREFIX}/* -f reference=${PTX_SANDBOX_PREFIX}/*

build:
	(\
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
		docker build -f ./core-sandbox/mongoseed.Dockerfile -t ${PTX_SANDBOX_PREFIX}/mongo-seed:${PDC_VER}-slim \
						$${TMP_DIR}/dataspace-connector/sandbox/infrastructure/utils/connector/mongo-seed/; \
		for bb in ${PTX_CORE}; do \
			docker build -f ./core-sandbox/$${bb}.Dockerfile -t ${PTX_SANDBOX_PREFIX}/$${bb}:${PDC_VER}-slim \
								$${TMP_DIR}/dataspace-connector/sandbox/infrastructure/; \
		done; \
		rm -rf $${TMP_DIR}; \
	)
	docker images -f reference=${PTX_PREFIX}/* -f reference=${PTX_SANDBOX_PREFIX}/*

run-pdc:
	cd pdc && docker compose up

stop-pdc:
	cd pdc && docker compose down -v

run-sandbox:
	cd core-sandbox && docker compose up

stop-sandbox:
	cd core-sandbox && docker compose down -v

run-catalog:
	@# cd pdc && docker compose up catalog
	docker ps -aq -f name=ptx-catalog | xargs -r docker rm -f
	docker run -d --name ptx-catalog -p 3002:8082 --no-healthcheck \
					--add-host host.docker.internal:host-gateway -ti ptx-sandbox/catalog:${PDC_VER}-slim
	docker ps -f name=ptx-catalog

purge:
	docker image ls -q -f reference=${PTX_PREFIX}/* -f reference=${PTX_SANDBOX_PREFIX}/* | xargs -r docker rmi -f

.PHONY: build-orig build run-catalog run-pdc stop-pdc run-core stop-core purge
.DEFAULT_GOAL := build
