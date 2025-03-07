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
PTX_CORE_PREFIX := ptx-core
PDC_REPO := git@github.com:Prometheus-X-association/dataspace-connector.git
PDC_VER := 1.8.2
PDC_ENV := production

setup:
	(\
	TMP_DIR=$$(mktemp -d) && cd $${TMP_DIR}; \
	git clone ${PDC_REPO}; \
	cd dataspace-connector; \
	git switch --detach v${PDC_VER}; \
	# docker compose build; \
	docker build -f ./docker/app/Dockerfile --build-arg ENV=${PDC_ENV} -t ${PTX_PREFIX}/connector:${PDC_VER} .; \
	docker build -f ./docker/mongodb/Dockerfile -t ${PTX_PREFIX}/mongodb:${PDC_VER} .; \
	cd sandbox/infrastructure; \
	for bb in catalog contract consent;do \
	    docker build -f ./utils/$${bb}/Dockerfile -t ${PTX_CORE_PREFIX}/$${bb}:${PDC_VER} .; \
	done; \
	rm -rf $${TMP_DIR}; \
	)
	docker images -f reference=${PTX_PREFIX}/* -f reference=${PTX_CORE_PREFIX}/*

run-catalog:
	@# docker run --rm --name ptx-catalog -p 3002:8082 --no-healthcheck --add-host host.docker.internal:host-gateway
	@# 				-ti ptx-core/catalog:1.8.2
	cd pdc && docker compose up catalog

run-pdc:
	cd pdc && docker compose up

stop-pdc:
	cd pdc && docker compose down -v

purge:
	docker image ls -q -f reference=${PTX_PREFIX}/* -f reference=${PTX_CORE_PREFIX}/* | xargs -r docker rmi -f

.PHONY: setup purge
.DEFAULT_GOAL := setup
