# Copyright 2026 Janos Czentye
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

ROOT_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
CREDS := exchange.env
DOCK_COMP := docker compose -f ${ROOT_DIR}/docker-compose.yaml --env-file=${ROOT_DIR}/creds/${CREDS}

########################################################################################################################

build ::
	./setup_pdc.sh
	${DOCK_COMP} build

setup ::
	${DOCK_COMP} up --force-recreate --abort-on-container-exit

setup-all ::
	${DOCK_COMP} --profile extra up --force-recreate --abort-on-container-exit

restart :: | teardown setup

########################################################################################################################

test-config ::
	./test_config.sh

test-credential ::
	./test_credential.sh

test-exchange ::
	$(eval SINCE := $(shell date -u +"%Y-%m-%dT%H:%M:%SZ"))
	@echo "Test start time: ${TS}"
	./test_exchange.sh
	@echo -e "\n#### Generated test case logs (since ${SINCE}):\n"
	SINCE=${SINCE} ${MAKE} -s logs

########################################################################################################################

logs ::
	${DOCK_COMP} logs api-provider pdc-provider pdc-consumer api-consumer --since="${SINCE}"

status ::
	${DOCK_COMP} ps -a

teardown ::
	${DOCK_COMP} --profile extra down -v

purge ::
	docker image ls -qf "reference=dataspace-connector" | xargs -r docker rmi -f || true
	docker rmi mongo:latest \
				ngrok/ngrok:latest \
				busybox:latest \
				traefik/whoami:latest \
				alpine/tshark:latest || true

########################################################################################################################

SHELL := bash
.SILENT:	# Set silent mode (-s) by default
.DEFAULT_GOAL := setup
