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

IMG="ptx-edge/rest-api:1.0"
API=rest-api
PREFIX="ptx-edge/v1"

#----------------------------------------------------------------------------------------------------------------------

oneTimeSetUp() {
    echo "Build images..."
    pushd ../../src/rest-api && make build && popd || return "${SHUNIT_ERROR}"
    echo "Setup cluster..."
    k3d cluster create "${CLUSTER}" --wait --timeout=30s --config="${CLUSTER_CFG}"
    k3d cluster list "${CLUSTER}" >/dev/null || return "${SHUNIT_ERROR}"
    # Avoid double teardown
    export clusterIsCreated="true"
    echo "Load images..."
    k3d image import -c "${CLUSTER}" "${IMG}" || return "${SHUNIT_ERROR}"
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

testPTXEdgeRESTAPI() {
    kubectl -n "${PTX}" apply -f ../manifests/ptx-edge-restapi_deployment.yaml
    kubectl -n "${PTX}" wait --for="condition=Available" --timeout=20s "deployment/${API}"
    assertTrue "$?"
    #
    kubectl -n "${PTX}" apply -f ../manifests/ptx-edge-restapi_service.yaml
    kubectl -n "${PTX}" apply -f ../manifests/ptx-edge-restapi_ingress.yaml
    kubectl -n "${PTX}" wait --for=jsonpath='{.status.loadBalancer.ingress[].ip}' --timeout=30s "ingress/${API}"
    assertTrue "$?"
    #
    kubectl -n "${PTX}" get nodes,all,endpoints,ingress -o wide
    #
    echo "Waiting for ingress to set up..." && sleep 15
    INGRESS_IP=$(kubectl -n "${PTX}" get "ingress/${API}" -o jsonpath='{.status.loadBalancer.ingress[].ip}')
    #
    echo "Check ==> http://${INGRESS_IP}:80/${PREFIX}/ui/"
    HTTP_RESP=$(curl -SsLI -o /dev/null -w "%{http_code}" "http://${INGRESS_IP}:80/${PREFIX}/ui/")
    assertSame "HTTP port expose failed" "200" "${HTTP_RESP}"
    #
    echo "Check ==> https://${INGRESS_IP}:443/${PREFIX}/ui/"
    HTTP_RESP=$(curl -SsLI -o /dev/null -w "%{http_code}" -k "https://${INGRESS_IP}:443/${PREFIX}/ui/")
    assertSame "HTTPS port expose failed" "200" "${HTTP_RESP}"
    #
    echo "Check ==> http://localhost:8080/${PREFIX}/ui/"
    HTTP_RESP=$(curl -SsLI -o /dev/null -w "%{http_code}" "http://localhost:8080/${PREFIX}/ui/")
    assertSame "Local port expose failed" "200" "${HTTP_RESP}"
}

#----------------------------------------------------------------------------------------------------------------------

source shunit2