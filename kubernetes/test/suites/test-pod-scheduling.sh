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

CPOD=cpu-huge-pod
MPOD=mem-huge-pod

source "${ROOT_DIR}"/test/scripts/helper.sh

#----------------------------------------------------------------------------------------------------------------------

oneTimeSetUp() {
    LOG "Setup cluster..."
    k3d cluster create "${CLUSTER}" --wait --timeout=30s --config="${CLUSTER_CFG}"
    k3d cluster list "${CLUSTER}" >/dev/null || return "${SHUNIT_ERROR}"
    # Avoid double teardown
    export clusterIsCreated="true"
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
        LOG "Delete cluster..."
        k3d cluster delete "${CLUSTER}"
        # Avoid double teardown
        export clusterIsCreated="false"
    fi
}

#----------------------------------------------------------------------------------------------------------------------

testSchedulingWithCPUConstraint() {
    LOG "Create CPU restricted pod..."
    kubectl -n "${PTX}" apply -f "${ROOT_DIR}"/test/manifests/ptx-edge-chuge_test_pod.yaml
    kubectl -n "${PTX}" wait --for="condition=Ready" --timeout=5s pod/"${CPOD}"
    assertFalse "pod creation not failed!" "$?"
    #
    log "Check pod status..."
    kubectl -n ${PTX} get pod/"${CPOD}"
    STATUS=$(kubectl -n "${PTX}" get pod/"${CPOD}" -o jsonpath="{.status.phase}")
    assertSame "Pod status is not pending!" "Pending" "${STATUS}"
    #
    log "Check scheduling decision..."
    kubectl -n ${PTX} events --types=Warning
    REASON=$(kubectl -n "${PTX}" get pod/"${CPOD}" -o jsonpath="{.status.conditions[].message}")
    assertTrue "Pod scheduling failed unexpectedly!" "[ $(expr "${REASON}" : '.*Insufficient cpu.*' ) -ne 0 ]"
}

testSchedulingWithMemoryConstraint() {
    LOG "Create CPU restricted pod..."
    kubectl -n "${PTX}" apply -f "${ROOT_DIR}"/test/manifests/ptx-edge-mhuge_test_pod.yaml
    kubectl -n "${PTX}" wait --for="condition=Ready" --timeout=5s pod/"${MPOD}"
    assertFalse "pod creation not failed!" "$?"
    #
    log "Check pod status..."
    kubectl -n ${PTX} get pod/"${MPOD}"
    STATUS=$(kubectl -n "${PTX}" get pod/"${MPOD}" -o jsonpath="{.status.phase}")
    assertSame "Pod status is not pending!" "Pending" "${STATUS}"
    #
    log "Check scheduling decision..."
    kubectl -n ${PTX} events --types=Warning
    REASON=$(kubectl -n "${PTX}" get pod/"${MPOD}" -o jsonpath="{.status.conditions[].message}")
    assertTrue "Pod scheduling failed unexpectedly!" "[ $(expr "${REASON}" : '.*Insufficient memory.*' ) -ne 0 ]"
}

#----------------------------------------------------------------------------------------------------------------------

source shunit2