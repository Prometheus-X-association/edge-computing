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
NAME := ptx-edge
NAMESPACE := ptx-edge
NAMESPACE_SANDBOX := ptx-sandbox
TIMEOUT ?= 300s

########################################################################################################################

install ::
	helm install --namespace=${NAMESPACE} --create-namespace ${NAME} --debug ./ \
		--set gateway.host=${GATEWAY_HOST} \
		--set gateway.port=${GATEWAY_PORT} \
		--set registry.url=${REGISTRY_URL} \
		--set registry.port=${REGISTRY_PORT} \
		--set connector.credential.serviceKey=${SERVICE_KEY} \
		--set connector.credential.secretKey=${SECRET_KEY} \
		--set sandbox.ns=${NAMESPACE_SANDBOX}

local-install ::
	helm upgrade --install --namespace=${NAMESPACE} --create-namespace ${NAME} --debug ./ \
		--set gateway.host="training.k3d.localhost" \
		--set gateway.port=4443 \
		--set registry.url="registry.k3d.local" \
		--set registry.port=5000 \
		--set connector.credential.serviceKey="dWJUUKH9rYF9wr_UAPb6PQXW9h17G7dzuGCbiDhcyjCGgHzLwBp6QHOQhDg0FFxS24GD8nvw37oe_LOjl7ztNATYiVOd_ZEVHQpV" \
		--set connector.credential.secretKey="Qh4XvuhSJbOp8nMV1JtibAUqjp3w_efBeFUfCmqQW_Nl8x4t3Sk6fWiK5L05CB3jhKZOgY5JlBSvWkFBHH_6fFhYQZWXNoZxO78x" \
		--set sandbox.ns=${NAMESPACE_SANDBOX} \
		--wait --timeout=${TIMEOUT}

lint ::
	helm lint ./

dry-run :: lint
	helm dependency build
	helm install --namespace=${NAMESPACE} --debug --dry-run=client ${NAME} ./ \
		--set gateway.proto="https" --set gateway.host="gw.example.com" --set gateway.port=1234 \
		--set registry.url="registry.k3d.local" --set registry.port=5000 \
		--set connector.credential.serviceKey="testServiceKey1234" \
		--set connector.credential.secretKey="testSecretKey1234" \
		--set connector.credential.triggerKey="testTriggerKey1234" \
		--set localRegistry.rootCAFileContent="$$(echo "----BEGIN CERTIFICATE-----test----BEGIN CERTIFICATE-----")"

teardown ::
	helm uninstall --namespace=${NAMESPACE} ${NAME} --debug --cascade=foreground --wait --timeout=30s
	#kubectl delete namespace ${NAMESPACE}

status ::
	helm dependency list
	@echo
	helm status --namespace=${NAMESPACE} ${NAME} || true
	@echo
	helm list -A || true
	@echo -e "\n>>> Namespace: ${NAMESPACE_SANDBOX}\n"
	kubectl -n ${NAMESPACE_SANDBOX} get all || true
	@echo -e "\n>>> Namespace: ${NAMESPACE}\n"
	kubectl -n ${NAMESPACE} get all,secrets,configmaps,middlewares,ingresses || true

########################################################################################################################

SHELL := bash
.SILENT:	# Set silent mode (-s) by default
.DEFAULT_GOAL := install