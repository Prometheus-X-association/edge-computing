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

LOG "Creating K3s test environment..."
k3d --wait --timeout="${TIMEOUT}s" cluster create "${CLUSTER}" --port 8080:80@loadbalancer --servers=1 --agents=0
kubectl cluster-info

log "Create Zone A"
k3d --wait --timeout="${TIMEOUT}s" node create "${NODE_A}" --cluster="${CLUSTER}" --replicas=2 --role=agent
kubectl label "node/k3d-${NODE_A}-0" "node/k3d-${NODE_A}-1" "node-role.kubernetes.io/worker=true" \
                                                            "disktype=hdd" \
                                                            "privacy-zone.dataspace.prometheus-x.org/${PZ_A}=true"
kubectl label "node/k3d-${NODE_A}-0" "connector.dataspace.prometheus-x.org/enabled=true"

log "Create Zone B"
k3d --wait --timeout="${TIMEOUT}s" node create "${NODE_B}" --cluster="${CLUSTER}" --replicas=2 --role=agent
kubectl label "node/k3d-${NODE_B}-0" "node/k3d-${NODE_B}-1" "node-role.kubernetes.io/worker=true" \
                                                            "disktype=ssd" \
                                                            "privacy-zone.dataspace.prometheus-x.org/${PZ_B}=true"
kubectl label "node/k3d-${NODE_B}-0" "connector.dataspace.prometheus-x.org/enabled=true"

log "Add multi-zone node"
k3d --wait --timeout="${TIMEOUT}s" node create "${NODE_AB}" --cluster="${CLUSTER}" --replicas=1 --role=agent
kubectl label "node/k3d-${NODE_AB}-0" "node-role.kubernetes.io/worker=true" \
                                      "disktype=hdd" \
                                      "privacy-zone.dataspace.prometheus-x.org/${PZ_A}=true" \
                                      "privacy-zone.dataspace.prometheus-x.org/${PZ_B}=true"

log "Build PTX-edge components..."
make -C ../../src/rest-api build
make -C ../../src/builder build
make -C ../ptx build

log "Load PTX-edge component images"
k3d image import -c "${CLUSTER}" "${API_IMG}" "${BUILD_IMG}" "${PDC_IMG}" "${MONGODB_IMG}"

log "Created K3s nodes"
kubectl get nodes -L "privacy-zone.dataspace.prometheus-x.org/${PZ_A}" \
                  -L "privacy-zone.dataspace.prometheus-x.org/${PZ_B}"

########################################################################################################################

echo -e "\nDone."