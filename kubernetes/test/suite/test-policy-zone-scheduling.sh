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

CLUSTER=test-cluster
PTX=ptx-edge
PZ_LAB='privacy-zone.dataspace.prometheus-x.org'

#----------------------------------------------------------------------------------------------------------------------

oneTimeSetUp() {
    echo "Setup cluster..."
    k3d cluster create ${CLUSTER} --wait --timeout=30s --config=../manifests/k3d-test_cluster_multi.yaml
    #
    export clusterIsSetUP="true"
}

setUp() {
    echo "Create namespace..."
    kubectl create namespace ${PTX}
}

tearDown() {
    # shellcheck disable=SC2154
    [[ "${_shunit_name_}" == 'EXIT' ]] && return 0
    echo "Delete namespace..."
    kubectl delete namespace ${PTX} --ignore-not-found --now
}

oneTimeTearDown() {
    if [[ "${clusterIsSetUP}" == "true" ]]; then
        echo "Delete cluster..."
        k3d cluster delete ${CLUSTER}
        #
        unset -v clusterIsSetUP
    fi
}

#----------------------------------------------------------------------------------------------------------------------

testPolicyZoneSchedulingFeature() {
    kubectl -n ${PTX} apply -f ../manifests/privacy_zone_restricted_test_pod.yaml
    kubectl -n ${PTX} wait --for="condition=Ready" --timeout=20s pod/pz-restricted-pod
    #
    kubectl get nodes -o wide -L ${PZ_LAB}/zone-A -L ${PZ_LAB}/zone-B -L ${PZ_LAB}/zone-C
    kubectl -n ${PTX} get pod/pz-restricted-pod -o wide
    #
    _node=$(kubectl -n ${PTX} get pod/pz-restricted-pod -o jsonpath="{.spec.nodeName}")
    #
    assertSame "k3d-${CLUSTER}-agent-0" "${_node}"
}

#----------------------------------------------------------------------------------------------------------------------

source shunit2