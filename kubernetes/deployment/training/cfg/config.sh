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
set -o allexport    # Also export all defined variables for 'envsubst'

########################################################################################################################

# Define base path for absolute file access
SCRIPT_DIR=$(readlink -f "$(dirname "$0")/..")
ROOT_DIR=$(readlink -f "${SCRIPT_DIR}/../..")

# Import essentials as logging, etc.
source "${ROOT_DIR}/test/scripts/helper.sh"

# Set colorful logging if available
if command -v kubecolor >/dev/null 2>&1; then
    KUBECOLOR_FORCE_COLORS=auto
    KUBECOLOR_PRESET="dark"
    KCTL=kubecolor
else
    KCTL=kubectl
fi

# Import additional confidential configurations from creds folder
for cfg in "${SCRIPT_DIR}"/creds/*.sh; do
    source "${cfg}"
done

########################################################################################################################

# Fundamental cluster configuration
TIMEOUT=120
CLUSTER="training"
ENV="demo"
NODE_DATA="node-data"
NODE_FED="node-federated"

# Registry
REGISTRY="registry.k3d.local"
REGISTRY_PORT=5000
# Loaded from creds/cluster-creds.sh !
### REGISTRY_USER=
### REGISTRY_SECRET=
K3D_REG="registry.k3d.localhost:${REGISTRY_PORT}"
REG_CREDS="${REGISTRY_USER}:${REGISTRY_SECRET}"
CA_DIR="${ROOT_DIR}/src/registry/.certs/ca"

# Loadbalancer
LB_WEB_PORT=8080
LB_WEBSECURE_PORT=8443
LB_DOMAIN="${CLUSTER}.k3d.localhost"
# Loaded from creds/websecure-creds.sh !
### GW_DOMAIN=
### GW_PORT=
CLUSTER_HOST="${LB_DOMAIN}:${LB_WEBSECURE_PORT}"
GW_HOST="${GW_DOMAIN}:${GW_PORT}"

PRIMARY_IP="$(ip route get 1 | awk '{print $(NF-2);exit}')"
PRIMARY_HOST="${PRIMARY_IP}:${LB_WEBSECURE_PORT}"

CLUSTER_TLS_SECRET="cluster-websecure-tls"

########################################################################################################################

# PTX namespace
PTX="ptx-edge"

# Used PTX-related labels
LAB_PZ="privacy-zone.dataspace.ptx.org"
LAB_WORK="node-role.kubernetes.io/worker=true"
LAB_PDC="connector.dataspace.ptx.org/enabled=true"

# Privacy zones
PZ_DATA_0="zone-data-0"
PZ_DATA_1="zone-data-1"
PZ_FED="zone-federated"

# PTX-edge components
COMPONENTS=(builder controller ptx registry rest-api scheduler)
#
BUILD_IMG="ptx-edge/builder:1.0"
CONTROL_IMG="ptx-edge/controller:1.0"
PDC_IMG="ptx/connector:1.10.0-slim"
MONGODB_IMG="ptx/mongodb:8.0.5-slim"
API_IMG="ptx-edge/rest-api:1.0"
SCHED_IMG="ptx-edge/scheduler:1.0"

# PTX-core components
CATALOG_IMG="ptx-sandbox/catalog:1.10.0-slim"
SANDBOX="ptx-sandbox"
CATALOG="catalog"
CATALOG_DNS="${CATALOG}.${SANDBOX}.svc.cluster.local"

# API auth
# Loaded from creds/websecure-creds.sh !
### API_BASIC_USER=
### API_BASIC_PASSWORD=
API_CREDS_BASE64_ENCODED=$(htpasswd -Bnb "${API_BASIC_USER}" "${API_BASIC_PASSWORD}" | openssl base64 -A)

# PDC
PDC=pdc
PDC_PORT=3000
PDC_NODE_PORT=30003
PDC_ID='${PDC_ID}'  # placeholder
# Loaded from creds/cluster-creds.sh !
### PDC_SERVICE_KEY=
### PDC_SECRET_KEY=
PDC_SERVICE_KEY_BASE64_ENCODED=$(printf '%s' "${PDC_SERVICE_KEY}" | base64 -w0)
PDC_SECRET_KEY_BASE64_ENCODED=$(printf '%s' "${PDC_SECRET_KEY}" | base64 -w0)
PDC_CFG_SERVICE_KEY='${SERVICE_KEY}'  # placeholder
PDC_CFG_SECRET_KEY='${SECRET_KEY}'  # placeholder
#
PDC_PREFIX_DATA_0="${PTX}/${PZ_DATA_0}/${PDC}"
PDC_PREFIX_DATA_1="${PTX}/${PZ_DATA_1}/${PDC}"

IMAGES=("${BUILD_IMG}" "${CONTROL_IMG}" "${PDC_IMG}" "${MONGODB_IMG}" "${API_IMG}" "${SCHED_IMG}" "${CATALOG_IMG}")

########################################################################################################################

# REST-API
REST_API="rest-api"
API_PORT=8080
PREFIX="${PTX}/api/v1"

# Scheduler
SCHEDULER="scheduler"
SCHEDULER_METHOD="generic"
SCHEDULER_REF="${PTX}-${SCHEDULER}"

# Controller
CONTROLLER="controller"

# Builder
BUILDER=builder
BUILD_TIMEOUT=600

########################################################################################################################

# Demo configuration
FED_COMPONENTS=(ghcr.io/alelevente/data_processor:latest \
                ghcr.io/alelevente/aggregator:latest \
                ghcr.io/alelevente/orchestrator:latest)
#
DP0="data-processor-0"
DP0_DATA="http://cloud-26952.vm.fured.cloud.bme.hu:8201/train_data.npz"
#DP0_DATA="http://host.k3d.internal:9999/dp1/train_data.npz"
#DP0_DATA="https://github.com/czeni/sample-datasets/blob/main/federated/dp1/train_data.npz"
DP0_IMG="ghcr.io/alelevente/data_processor:latest"
DP0_MLFLOW_INT="http://localhost:5000"
DP0_MLFLOW_ORG="http://${DP0}.${PTX}:5000"
#
DP1="data-processor-1"
DP1_DATA="http://cloud-26952.vm.fured.cloud.bme.hu:8202/train_data.npz"
#DP1_DATA="http://host.k3d.internal:9999/dp2/train_data.npz"
#DP1_DATA="https://github.com/czeni/sample-datasets/blob/main/federated/dp2/train_data.npz"
DP1_IMG="ghcr.io/alelevente/data_processor:latest"
DP1_MLFLOW_INT="http://localhost:5000"
DP1_MLFLOW_ORG="http://${DP1}.${PTX}:5000"
#
AGG="aggregator"
AGG_IMG="ghcr.io/alelevente/aggregator:latest"
AGG_MLFLOW_INT="http://localhost:5000"
AGG_MLFLOW_ORG="http://${AGG}.${PTX}:5000"
AGG_MLFLOW_EXT="http://vm.fured.cloud.bme.hu:11686/worker/aggregator"
MLFLOW_API_PREFIX="api/2.0/mlflow"
#
ORCH="orchestrator"
ORCH_IMG="ghcr.io/alelevente/orchestrator:latest"