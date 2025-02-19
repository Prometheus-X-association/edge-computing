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

IMG="ptx-edge/builder:1.0"
BUILDER=builder
WORKER=worker
POD=pz-restricted-pod

source "${ROOT_DIR}"/test/suites/helper.sh

#----------------------------------------------------------------------------------------------------------------------

oneTimeSetUp() {
    log "Build images..."
    pushd "${ROOT_DIR}"/src/builder && make build && popd || return "${SHUNIT_ERROR}"
    #
    log "Setup cluster..."
    k3d cluster create "${CLUSTER}" --wait --timeout=60s --config="${CLUSTER_CFG}"
    k3d cluster list "${CLUSTER}" >/dev/null || return "${SHUNIT_ERROR}"
    # Avoid double teardown
    export clusterIsCreated="true"
    #
    log "Load images..."
    k3d image import -c "${CLUSTER}" -m 'direct' "${IMG}" || return "${SHUNIT_ERROR}"
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

testPTXEdgeStaticVolumeClaim() {
    log "Create static volume..."
	kubectl apply -f "${ROOT_DIR}"/test/manifests/ptx-edge-pz_restricted_storage.yaml
	kubectl apply -f "${ROOT_DIR}"/test/manifests/ptx-edge-pz_restricted_pv.yaml
	kubectl get storageclass,pv-o wide
	#
	log "Create consuming pod..."
	kubectl create namespace ${PTX}
	kubectl -n ${PTX} apply -f "${ROOT_DIR}"/test/manifests/ptx-edge-pz_restricted_pvc.yaml
	kubectl -n ${PTX} apply -f "${ROOT_DIR}"/test/manifests/ptx-edge-pz_pod_with_pvc.yaml
	kubectl get pvc,all -o wide
	#
	startSkipping
        kubectl -n ${PTX} wait --for='jsonpath={.status.phase}=Bound' --timeout=60s pvc/"${WORKER}"-pvc
        assertTrue "PVC binding failed!" "$?"
        kubectl -n ${PTX} wait --for="condition=Ready" --timeout=60s pod/"${POD}"
        assertTrue "PV acquisition failed!" "$?"
	endSkipping
}

testPTXEdgeDynamicVolumeClaim() {
    log "Create dynamic volume with consuming pod..."
	kubectl -n ${PTX} apply -f "${ROOT_DIR}"/test/manifests/ptx-edge-builder_worker_pvc.yaml
	kubectl -n ${PTX} apply -f "${ROOT_DIR}"/test/manifests/ptx-edge-pz_pod_with_pvc.yaml
	kubectl -n ${PTX} wait --for='jsonpath={.status.phase}=Bound' --timeout=60s pvc/"${WORKER}"-pvc
    assertTrue "PVC binding failed!" "$?"
    #
	kubectl -n ${PTX} get pv,pvc -o wide
	kubectl -n ${PTX} wait --for="condition=Ready" --timeout=60s pod/"${POD}"
	assertTrue "PV acquisition failed!" "$?"
	#
	kubectl -n ${PTX} get all,pv,pvc -o wide
}

testPTXEdgeBuilder() {
    log "Create dynamic volume with builder pod..."
	kubectl -n ${PTX} apply -f "${ROOT_DIR}"/test/manifests/ptx-edge-builder_worker_pvc.yaml
	kubectl -n ${PTX} apply -f "${ROOT_DIR}"/test/manifests/ptx-edge-builder_worker_job.yaml
	kubectl -n ${PTX} wait --for='jsonpath={.status.phase}=Bound' --timeout=60s pvc/"${WORKER}"-pvc
	assertTrue "PVC binding failed!" "$?"
	#
	kubectl -n ${PTX} get all,pv,pvc -o wide
	kubectl -n ${PTX} wait --for="condition=Complete" --timeout=60s job/${BUILDER}
	assertTrue "Job completion failed!" "$?"
	#
	kubectl -n ${PTX} get all,pv,pvc -o wide
}

#----------------------------------------------------------------------------------------------------------------------

source shunit2