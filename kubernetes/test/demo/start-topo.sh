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

SCRIPTS_DIR=$(readlink -f "$(dirname "$0")")
source "${SCRIPTS_DIR}/../scripts/helper.sh"

CLUSTER=demo
PZ_A=zone-a
PZ_B=zone-b
PZ_AB=zone-ab

API_IMG=ptx-edge/rest-api:1.0
BUILDER_IMG=ptx-edge/builder:1.0
PDC_IMG=ptx/connector:1.9.2-slim
MONGODB_IMG=ptx/mongodb:8.0.5-slim

LOG "Setting up test environment..."

k3d --wait --timeout=60s cluster create "${CLUSTER}" --port 8080:80@loadbalancer --servers=1 --agents=0
kubectl cluster-info

log "Create Zone A"
k3d --wait --timeout=60s node create "${PZ_A}" --cluster="${CLUSTER}" --replicas=2 --role=agent
kubectl label "node/k3d-${PZ_A}-0" "node/k3d-${PZ_A}-1" "privacy-zone.dataspace.prometheus-x.org/${PZ_A}=true"
kubectl label "node/k3d-${PZ_A}-0" "node/k3d-${PZ_A}-1" "node-role.kubernetes.io/worker=true"
kubectl label "node/k3d-${PZ_A}-0" "connector.dataspace.prometheus-x.org/enabled=true"

log "Create Zone B"
k3d --wait --timeout=60s node create "${PZ_B}" --cluster="${CLUSTER}" --replicas=2 --role=agent
kubectl label "node/k3d-${PZ_B}-0" "node/k3d-${PZ_B}-1" "privacy-zone.dataspace.prometheus-x.org/${PZ_B}=true"
kubectl label "node/k3d-${PZ_B}-0" "node/k3d-${PZ_B}-1" "node-role.kubernetes.io/worker=true"
kubectl label "node/k3d-${PZ_B}-0" "connector.dataspace.prometheus-x.org/enabled=true"

log "Add multizone node"
k3d --wait --timeout=60s node create "${PZ_AB}" --cluster="${CLUSTER}" --replicas=1 --role=agent
kubectl label "node/k3d-${PZ_AB}-0" "node-role.kubernetes.io/worker=true"
kubectl label "node/k3d-${PZ_AB}-0" "privacy-zone.dataspace.prometheus-x.org/${PZ_A}=true" \
                                    "privacy-zone.dataspace.prometheus-x.org/${PZ_B}=true"

log "Load PTX edge component"
k3d image import -c ${CLUSTER} ${API_IMG} ${BUILDER_IMG} ${PDC_IMG} ${MONGODB_IMG}

log "Created K8s nodes"
kubectl get nodes -L "privacy-zone.dataspace.prometheus-x.org/${PZ_A}" -L "privacy-zone.dataspace.prometheus-x.org/${PZ_B}"

echo -e "\nDone."