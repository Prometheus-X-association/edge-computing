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

CLUSTER=test-suite-cluster
CLUSTER_CFG=../manifests/k3d-test_cluster_multi.yaml
PTX=ptx-edge

PZ_LAB='privacy-zone.dataspace.prometheus-x.org'

#----------------------------------------------------------------------------------------------------------------------

oneTimeSetUp() {
    echo "Build images..."
    pushd ../../src/rest-api && make build && popd || return "${SHUNIT_ERROR}"
    echo "Setup cluster..."
    k3d cluster create "${CLUSTER}" --wait --timeout=30s --config="${CLUSTER_CFG}"
    k3d cluster list "${CLUSTER}" >/dev/null || return "${SHUNIT_ERROR}"
    # Avoid double teardown
    export clusterIsCreated="true"
}

setUp() {
    echo "Create namespace..."
    kubectl create namespace "${PTX}" || return "${SHUNIT_ERROR}"
}

tearDown() {
    # shellcheck disable=SC2154
    [[ "${_shunit_name_}" == 'EXIT' ]] && return 0
    echo "Delete resources..."
    kubectl -n "${PTX}" delete all --all --now
    kubectl delete namespace "${PTX}" --ignore-not-found --now
}

oneTimeTearDown() {
    if [[ "${clusterIsCreated:-true}" == "true" ]]; then
        echo "Delete cluster..."
        k3d cluster delete "${CLUSTER}"
        # Avoid double teardown
        export clusterIsCreated="false"
    fi
}

#----------------------------------------------------------------------------------------------------------------------

testPolicyZoneSchedulingFeature() {
    kubectl -n "${PTX}" apply -f ../manifests/ptx-edge-pz_restricted_pod.yaml
    kubectl -n "${PTX}" wait --for="condition=Ready" --timeout=20s pod/pz-restricted-pod
    assertTrue "$?"
    #
    kubectl get nodes -o wide -L "${PZ_LAB}/zone-A" -L "${PZ_LAB}/zone-B" -L "${PZ_LAB}/zone-C"
    kubectl -n "${PTX}" get pod/pz-restricted-pod -o wide
    #
    _node=$(kubectl -n "${PTX}" get pod/pz-restricted-pod -o jsonpath="{.spec.nodeName}")
    assertSame "k3d-${CLUSTER}-agent-0" "${_node}"
}

#----------------------------------------------------------------------------------------------------------------------

source shunit2