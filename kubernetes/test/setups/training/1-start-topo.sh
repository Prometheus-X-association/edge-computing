#!/usr/bin/env bash
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
set -eou pipefail
source config.sh

########################################################################################################################

LOG "Creating training infrastructure..."
envsubst <"${SCRIPT_DIR}/rsc/k3d-demo-cluster.yaml" | k3d cluster create --config=-
${KCTL} cluster-info

log "Create Privacy Zones: zone-tr-* for <TRAINING>"
k3d --wait --timeout="${TIMEOUT}s" node create "${NODE_TR}" --cluster="${CLUSTER}" --replicas=3 --role=agent
${KCTL} label "node/k3d-${NODE_TR}-0" "${LAB_WORK}" "${LAB_PDC}" "${LAB_PZ}/${PZ_TR_0}=true"
${KCTL} label "node/k3d-${NODE_TR}-1" "${LAB_WORK}" "${LAB_PDC}" "${LAB_PZ}/${PZ_TR_1}=true"
${KCTL} label "node/k3d-${NODE_TR}-2" "${LAB_WORK}" "${LAB_PDC}" "${LAB_PZ}/${PZ_TR_2}=true"

log "Create Privacy Zone: ${PZ_AG} for <AGGREGATION>"
k3d --wait --timeout="${TIMEOUT}s" node create "${NODE_AG}" --cluster="${CLUSTER}" --replicas=2 --role=agent
${KCTL} label "node/k3d-${NODE_AG}-0" "node/k3d-${NODE_AG}-1" "${LAB_WORK}" "${LAB_PZ}/${PZ_AG}=true"

log "Create Privacy Zone: ${PZ_OR} for <ORCHESTRATION>"
k3d --wait --timeout="${TIMEOUT}s" node create "${NODE_OR}" --cluster="${CLUSTER}" --replicas=1 --role=agent
${KCTL} label "node/k3d-${NODE_OR}-0" "${LAB_WORK}" "${LAB_PZ}/${PZ_OR}=true"

#log "Reserve mount points for persistent volumes..."
#docker container ls -qf "name=k3d-node-" -f "name=k3d-demo-server-" | xargs -rI {} docker exec {} sh -c 'mkdir -pv /var/cache/storage'

LOG "Load components into registry: ${K3D_REG}"
for img in ${PDC_IMG} ${MONGODB_IMG} ${BUILDER_IMG} ${API_IMG} ${SCHED_IMG} ${CATALOG_IMG}; do
    skopeo copy --dest-cert-dir="${CA_DIR}" --dest-creds="${REG_CREDS}" "docker-daemon:${img}" "docker://${K3D_REG}/${img}"
done
echo

log "Stored images in cluster"
curl -Sskf --cacert "${CA_DIR}/ca.crt" -u "${REG_CREDS}" -X GET "https://${K3D_REG}/v2/_catalog" | python3 -m json.tool

log "Created cluster nodes"
${KCTL} get nodes -L "${LAB_PZ}/${PZ_TR_0}" -L "${LAB_PZ}/${PZ_TR_1}" -L "${LAB_PZ}/${PZ_TR_2}" \
                    -L "${LAB_PZ}/${PZ_AG}" -L "${LAB_PZ}/${PZ_OR}"

log "Configured DNS entries"
${KCTL} -n kube-system get configmaps coredns -o jsonpath='{.data.NodeHosts}'

########################################################################################################################

echo -e "\nDone."