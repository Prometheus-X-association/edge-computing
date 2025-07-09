#!/usr/bin/env bash
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

# shunit2 does not support set -eu
set -o pipefail

ROOT_DIR=$(readlink -f "$(dirname "$0")/../..")
CLUSTER=test-suite-cluster
CLUSTER_CFG="${ROOT_DIR}"/test/manifests/k3d-test_cluster_multi.yaml
PTX=ptx-edge
SANDBOX=ptx-sandbox

CATALOG_IMG="ptx-sandbox/catalog:1.9.4-slim"
CATALOG=catalog
PDC_IMG="ptx/connector:1.9.4-slim"
MONGODB_IMG="ptx/mongodb:8.0.5-slim"
PDC=pdc
PDC_PORT=3000
PDC_NODE_PORT=30003
PDC_PREFIX=ptx-edge/pdc

source "${ROOT_DIR}"/test/scripts/helper.sh

#----------------------------------------------------------------------------------------------------------------------

oneTimeSetUp() {
    LOG "Build images..."
    pushd "${ROOT_DIR}"/src/ptx && make build && popd || return "${SHUNIT_ERROR}"
    #
    LOG "Setup cluster..."
    k3d cluster create "${CLUSTER}" --wait --timeout=60s --config="${CLUSTER_CFG}"
    k3d cluster list "${CLUSTER}" >/dev/null || return "${SHUNIT_ERROR}"
    # Avoid double teardown
    export clusterIsCreated="true"
    #
    LOG "Load images..."
    k3d image import -c "${CLUSTER}" -m 'direct' "${CATALOG_IMG}" "${PDC_IMG}" "${MONGODB_IMG}" || return "${SHUNIT_ERROR}"
    #
    LOG "Create PTX-core sandbox..."
    kubectl create namespace "${SANDBOX}"
	kubectl -n "${SANDBOX}" apply -f "${ROOT_DIR}"/test/manifests/ptx-sandbox-deployment.yaml
}

setUp() {
    LOG "Create namespace..."
    kubectl create namespace "${PTX}" || return "${SHUNIT_ERROR}"
    echo
}

tearDown() {
    # shellcheck disable=SC2154
    [[ "${_shunit_name_}" == 'EXIT' ]] && return 0
    LOG "Delete resources..."
    kubectl -n "${PTX}" delete all --all --now
    kubectl delete namespace "${PTX}" --ignore-not-found --now
}

oneTimeTearDown() {
    if [[ "${clusterIsCreated:-true}" == "true" ]]; then
        LOG "Tear down PTX-core sandbox..."
        kubectl delete namespace "${SANDBOX}" --ignore-not-found --now
        LOG "Delete cluster..."
        k3d cluster delete "${CLUSTER}"
        # Avoid double teardown
        export clusterIsCreated="false"
    fi
}

#----------------------------------------------------------------------------------------------------------------------

testPTXSandboxCatalog() {
    LOG "Validate catalog deployment..."
	kubectl -n "${SANDBOX}" wait --for="condition=Available" --timeout=20s deployment/"${CATALOG}"
	assertTrue "deployment creation failed!" "$?"
	#
	kubectl -n "${SANDBOX}" get all,endpoints -o wide
}

testPTXConnectorConfig() {
    LOG "Create PDC ConfigMaps..."
    kubectl -n "${PTX}" apply -f "${ROOT_DIR}"/test/manifests/ptx-edge-pdc_config.yaml \
                                                                        -l app.kubernetes.io/component!=cfg-envvars
    log "Apply new envvars for sandbox catalog..."
	kubectl -n "${PTX}" apply -f "${ROOT_DIR}"/test/manifests/ptx-sandbox-pdc_env.yaml
	log "Create PDC deployment..."
	kubectl -n "${PTX}" apply -f "${ROOT_DIR}"/test/manifests/ptx-edge-pdc_deployment.yaml
	kubectl -n "${PTX}" wait --for="condition=Available" --timeout=20s deployment/"${PDC}"
	assertTrue "PDC deployment creation failed!" "$?"
	#
	kubectl -n "${PTX}" get all,configmaps,secrets,endpointslices -o wide
}

testPTXConnector() {
    LOG "Create PDC deployment..."
    kubectl -n "${PTX}" apply -f "${ROOT_DIR}"/test/manifests/ptx-edge-pdc_config.yaml \
                                                                        -l app.kubernetes.io/component!=cfg-envvars
	kubectl -n "${PTX}" apply -f "${ROOT_DIR}"/test/manifests/ptx-sandbox-pdc_env.yaml
	kubectl -n "${PTX}" apply -f "${ROOT_DIR}"/test/manifests/ptx-edge-pdc_deployment.yaml
	kubectl -n "${PTX}" wait --for="condition=Available" --timeout=20s deployment/"${PDC}"
	assertTrue "PDC deployment creation failed!" "$?"
	#
	LOG "Expose PDC..."
	kubectl -n "${PTX}" create service nodeport "${PDC}" --tcp="${PDC_PORT}:${PDC_PORT}" --node-port="${PDC_NODE_PORT}"
	kubectl -n "${PTX}" wait --for=jsonpath='{.spec.clusterIP}' --timeout=20s service/"${PDC}"
	assertTrue "Node IP configuration failed!" "$?"
	#
	kubectl -n "${PTX}" get all,configmaps,secrets,endpointslices -o wide
	#
	log "Waiting for PDC to set up..."
	timeout 30 grep -m1 "Server running on" <(kubectl -n "${PTX}" logs deployments/"${PDC}" -fc ptx-connector)
	assertTrue "PDC setup failed!" "$?"
	#
	NODE_IP=$(kubectl -n ${PTX} get pod -l app=${PDC} -o jsonpath='{.items[].status.hostIP}')
	assertNotNull "Node IP not found!" "${NODE_IP}"
	#
	echo "Check ==> http://${NODE_IP}:${PDC_NODE_PORT}/"
	HTTP_RESP=$(curl -SsLI -o /dev/null -w "%{http_code}" "http://${NODE_IP}:${PDC_NODE_PORT}/")
	assertSame "Local port exposure failed!" "200" "${HTTP_RESP}"
}

#----------------------------------------------------------------------------------------------------------------------

source shunit2