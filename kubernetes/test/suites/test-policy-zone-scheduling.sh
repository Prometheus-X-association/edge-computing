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

POD=pz-restricted-pod
PZ_LAB='privacy-zone.dataspace.prometheus-x.org'

source "${ROOT_DIR}"/test/suites/helper.sh

#----------------------------------------------------------------------------------------------------------------------

oneTimeSetUp() {
    log "Build images..."
    pushd "${ROOT_DIR}"/src/rest-api && make build && popd || return "${SHUNIT_ERROR}"
    log "Setup cluster..."
    k3d cluster create "${CLUSTER}" --wait --timeout=30s --config="${CLUSTER_CFG}"
    k3d cluster list "${CLUSTER}" >/dev/null || return "${SHUNIT_ERROR}"
    # Avoid double teardown
    export clusterIsCreated="true"
}

setUp() {
    log "Create namespace..."
    kubectl create namespace "${PTX}" || return "${SHUNIT_ERROR}"
}

tearDown() {
    # shellcheck disable=SC2154
    [[ "${_shunit_name_}" == 'EXIT' ]] && return 0
    log "Delete resources..."
    kubectl -n "${PTX}" delete all --all --now
    kubectl delete namespace "${PTX}" --ignore-not-found --now
}

oneTimeTearDown() {
    if [[ "${clusterIsCreated:-true}" == "true" ]]; then
        log "Delete cluster..."
        k3d cluster delete "${CLUSTER}"
        # Avoid double teardown
        export clusterIsCreated="false"
    fi
}

#----------------------------------------------------------------------------------------------------------------------

testPolicyZoneSchedulingWithNodeSelector() {
    log "Create Privacy Zone restricted pod..."
    kubectl -n "${PTX}" apply -f "${ROOT_DIR}"/test/manifests/ptx-edge-pz_selected_test_pod.yaml
    kubectl -n "${PTX}" wait --for="condition=Ready" --timeout=60s pod/"${POD}"
    assertTrue "pod creation failed!" "$?"
    #
    kubectl get nodes -o wide -L "${PZ_LAB}/zone-A" -L "${PZ_LAB}/zone-B" -L "${PZ_LAB}/zone-C"
    kubectl -n "${PTX}" get pod/"${POD}" -o wide
    #
    NODE=$(kubectl -n "${PTX}" get pod/"${POD}" -o jsonpath="{.spec.nodeName}")
    assertNotNull "node name not found!" "${NODE}"
    echo -e "\nSelected node: ${NODE}\n"
    assertSame "pod scheduling failed!" "k3d-${CLUSTER}-agent-0" "${NODE}"
}

testPolicyZoneSchedulingWithNodeAffinity() {
    log "Create Privacy Zone restricted pod..."
    kubectl -n "${PTX}" apply -f "${ROOT_DIR}"/test/manifests/ptx-edge-pz_affined_test_pod.yaml
    kubectl -n "${PTX}" wait --for="condition=Ready" --timeout=60s pod/"${POD}"
    assertTrue "pod creation failed!" "$?"
    #
    kubectl get nodes -o wide -L "${PZ_LAB}/zone-A" -L "${PZ_LAB}/zone-B" -L "${PZ_LAB}/zone-C"
    kubectl -n "${PTX}" get pod/"${POD}" -o wide
    #
    NODE=$(kubectl -n "${PTX}" get pod/"${POD}" -o jsonpath="{.spec.nodeName}")
    assertNotNull "node name not found!" "${NODE}"
    echo -e "\nSelected node: ${NODE}\n"
    assertSame "pod scheduling failed!" "k3d-${CLUSTER}-agent-0" "${NODE}"
}

#----------------------------------------------------------------------------------------------------------------------

source shunit2