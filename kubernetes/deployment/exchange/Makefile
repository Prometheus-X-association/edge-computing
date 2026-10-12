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
DOCKER_INFRA := docker compose --env-file=${ROOT_DIR}/creds/${CREDS}
COMPOSE_BASE := $(DOCKER_INFRA) --compatibility -f ${ROOT_DIR}/basic-infra.yaml
COMPOSE_EXCHANGE := $(DOCKER_INFRA) -f ${ROOT_DIR}/docker-compose.yaml

########################################################################################################################

build ::
	./scripts/setup_pdc.sh
	${COMPOSE_EXCHANGE} --profile extra build

setup-base ::
	${COMPOSE_BASE} up --renew-anon-volumes --force-recreate --abort-on-container-failure  || true

setup ::
	${COMPOSE_EXCHANGE} up --renew-anon-volumes --force-recreate --abort-on-container-failure || true

setup-all ::
	${COMPOSE_EXCHANGE} --profile extra up --renew-anon-volumes --force-recreate --abort-on-container-failure || true

restart :: | teardown setup

########################################################################################################################

test-config-api ::
	./tests/test_config_api.sh

test-config-file ::
	./tests/test_config_file.sh

test-credentials ::
	./tests/test_credentials.sh

test-exchange-consumer ::
	$(eval SINCE := $(shell date -u +"%Y-%m-%dT%H:%M:%SZ"))
	@echo "Test start time: ${SINCE}"
	./tests/test_exchange_consumer.sh
	@echo -e "\n#### Generated test case logs (since ${SINCE}):\n"
	SINCE=${SINCE} ${MAKE} -s logs

test-exchange-api-consumption ::
	$(eval SINCE := $(shell date -u +"%Y-%m-%dT%H:%M:%SZ"))
	@echo "Test start time: ${SINCE}"
	./tests/test_exchange_api_consumption.sh
	@echo -e "\n#### Generated test case logs (since ${SINCE}):\n"
	SINCE=${SINCE} ${MAKE} -s logs

test-service-chain-basic-consumer ::
	$(eval SINCE := $(shell date -u +"%Y-%m-%dT%H:%M:%SZ"))
	@echo "Test start time: ${SINCE}"
	./tests/test_service_chain_basic_consumer.sh
	@echo -e "\n#### Generated test case logs (since ${SINCE}):\n"
	SINCE=${SINCE} ${MAKE} -s logs

test-service-chain-basic-provider ::
	$(eval SINCE := $(shell date -u +"%Y-%m-%dT%H:%M:%SZ"))
	@echo "Test start time: ${SINCE}"
	./tests/test_service_chain_basic_provider.sh
	@echo -e "\n#### Generated test case logs (since ${SINCE}):\n"
	SINCE=${SINCE} ${MAKE} -s logs

########################################################################################################################

logs ::
	@echo -e "\n@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\n"
	${COMPOSE_EXCHANGE} logs api-provider --since="${SINCE}"
	@echo
	${COMPOSE_EXCHANGE} logs api-provider-status --since="${SINCE}"
	@echo -e "\n@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\n"
	${COMPOSE_EXCHANGE} logs pdc-provider --since="${SINCE}"
	@echo -e "\n@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\n"
	${COMPOSE_EXCHANGE} logs pdc-consumer --since="${SINCE}"
	@echo -e "\n@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\n"
	${COMPOSE_EXCHANGE} logs api-consumer --since="${SINCE}"

	@echo -e "\n@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\n"
	${COMPOSE_EXCHANGE} logs traefik-proxy --since="${SINCE}"
	@echo -e "\n@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\n"
	${COMPOSE_EXCHANGE} logs sniffer-provider --since="${SINCE}"
	@echo
	${COMPOSE_EXCHANGE} logs sniffer-consumer --since="${SINCE}"

attached ::
	${COMPOSE_EXCHANGE} logs --follow -t || true

status ::
	${COMPOSE_EXCHANGE} ps -a

teardown ::
	${COMPOSE_EXCHANGE} --profile extra down -v

purge ::
	${COMPOSE_EXCHANGE} --profile extra down -v --rmi=all

########################################################################################################################

SHELL := bash
.SILENT:	# Set silent mode (-s) by default
.DEFAULT_GOAL := setup
