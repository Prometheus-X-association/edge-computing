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
set -eou pipefail
source config.sh

########################################################################################################################

LOG "Assemble demo components..."

log "Build PTX-edge components..."
make -C "${ROOT_DIR}/src/registry" build
make -C "${ROOT_DIR}/src/builder" build
make -C "${ROOT_DIR}/src/rest-api" build
make -C "${ROOT_DIR}/src/scheduler" build
make -C "${ROOT_DIR}/src/samples" build-all publish-all

log "Build PTX-core sandbox components..."
make -C "${ROOT_DIR}/src/ptx" build

LOG "Creating demo environment..."
#k3d --wait --timeout="${TIMEOUT}s" cluster create "${CLUSTER}" --port 8080:80@loadbalancer --servers=1 --agents=0
envsubst <"${SCRIPT_DIR}/rsc/k3d-demo-cluster.yaml" | k3d cluster create --config=-
${KCTL} cluster-info

log "Create Zone A"
k3d --wait --timeout="${TIMEOUT}s" node create "${NODE_A}" --cluster="${CLUSTER}" --replicas=2 --role=agent
${KCTL} label "node/k3d-${NODE_A}-0" "node/k3d-${NODE_A}-1" \
                "disktype=hdd" \
                "node-role.kubernetes.io/worker=true" \
                "privacy-zone.dataspace.ptx.org/${PZ_A}=true"
${KCTL} label "node/k3d-${NODE_A}-0" \
                "connector.dataspace.ptx.org/enabled=true"

log "Create Zone B"
k3d --wait --timeout="${TIMEOUT}s" node create "${NODE_B}" --cluster="${CLUSTER}" --replicas=2 --role=agent
${KCTL} label "node/k3d-${NODE_B}-0" "node/k3d-${NODE_B}-1" \
                "disktype=ssd" \
                "node-role.kubernetes.io/worker=true" \
                "privacy-zone.dataspace.ptx.org/${PZ_B}=true"
${KCTL} label "node/k3d-${NODE_B}-0" \
                "connector.dataspace.ptx.org/enabled=true"

log "Add multi-zone node"
k3d --wait --timeout="${TIMEOUT}s" node create "${NODE_AB}" --cluster="${CLUSTER}" --replicas=1 --role=agent
${KCTL} label "node/k3d-${NODE_AB}-0" \
                "disktype=hdd" \
                "node-role.kubernetes.io/worker=true" \
                "privacy-zone.dataspace.ptx.org/${PZ_A}=true" \
                "privacy-zone.dataspace.ptx.org/${PZ_B}=true"

LOG "Load components into registry: ${K3D_REG}"
for img in ${PDC_IMG} ${MONGODB_IMG} ${BUILDER_IMG} ${API_IMG} ${SCHED_IMG} ${CATALOG_IMG}; do
    skopeo copy --dest-cert-dir="${CA_DIR}" --dest-creds="${REG_CREDS}" "docker-daemon:${img}" "docker://${K3D_REG}/${img}"
done

echo

log "Stored images"
curl -Sskf --cacert "${CA_DIR}/ca.crt" -u "${REG_CREDS}" -X GET "https://${K3D_REG}/v2/_catalog" | python3 -m json.tool

log "Created cluster nodes"
${KCTL} get nodes -o wide -L "privacy-zone.dataspace.ptx.org/${PZ_A}" -L "privacy-zone.dataspace.ptx.org/${PZ_B}"

log "Configured DNS entries"
${KCTL} -n kube-system get configmaps coredns -o jsonpath='{.data.NodeHosts}'

########################################################################################################################

echo -e "\nDone."