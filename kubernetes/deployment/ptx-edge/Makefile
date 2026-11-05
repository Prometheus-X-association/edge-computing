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

########################################################################################################################

install ::
	helm upgrade --install --namespace=${NAMESPACE} ${NAME} ./

lint ::
	helm lint ./

dry-run :: lint
	helm install --namespace=${NAMESPACE} --debug --dry-run=client ${NAME} ./ \
		--set gateway.proto="https" --set gateway.host="example.gw.com" --set gateway.port=1234 \
		--set registry.url="registry.k3d.local" --set registry.port=5000 \
		--set connector.credential.serviceKey="service1234" \
		--set connector.credential.secretKey="secret1234" \
		--set connector.credential.triggerKey="trigger1234"

teardown ::
	helm uninstall --namespace=${NAMESPACE} ${NAME}

status ::
	helm status --namespace=${NAMESPACE} ${NAME}

########################################################################################################################

SHELL := bash
.SILENT:	# Set silent mode (-s) by default
.DEFAULT_GOAL := install