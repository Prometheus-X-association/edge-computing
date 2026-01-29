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
set -o allexport    # Also export all variables for envsubst

# Logging
SCRIPT_DIR=$(readlink -f "$(dirname "$0")")
ROOT_DIR=$(readlink -f "${SCRIPT_DIR}/../../..")

source "${ROOT_DIR}/test/scripts/helper.sh"

if command -v kubecolor >/dev/null 2>&1; then
    KUBECOLOR_FORCE_COLORS=auto
    KUBECOLOR_PRESET="dark"
    KCTL=kubecolor
else
    KCTL=kubectl
fi

# Deployment/cluster/component credentials
source "${SCRIPT_DIR}/creds/cluster-creds.sh"

# Cluster
TIMEOUT=60
CLUSTER="training"
ENV="demo"
NODE_TR="node-tr"
NODE_AG="node-ag"
NODE_OR="node-or"

# Labels
LAB_PZ="privacy-zone.dataspace.ptx.org"
LAB_WORK="node-role.kubernetes.io/worker=true"
LAB_PDC="connector.dataspace.ptx.org/enabled=true"

# Privacy zones
PZ_TR_0="zone-tr-0"
PZ_TR_1="zone-tr-1"
PZ_TR_2="zone-tr-2"
PZ_AG="zone-ag"
PZ_OR="zone-or"

# Registry
REGISTRY="registry.k3d.local"
REGISTRY_PORT=5000
REGISTRY_USER="admin"
REGISTRY_SECRET="admin"
#
K3D_REG="registry.k3d.localhost:${REGISTRY_PORT}"
REG_CREDS="${REGISTRY_USER}:${REGISTRY_SECRET}"
CA_DIR="${ROOT_DIR}/src/registry/.certs/ca"

# Loadbalancer
LB_PORT=8080
LB_DOMAIN="${CLUSTER}.k3d.localhost"
LB_HOST="${LB_DOMAIN}:${LB_PORT}"

# PTX-edge components
API_IMG="ptx-edge/rest-api:1.0"
PDC_IMG="ptx/connector:1.10.0-slim"
MONGODB_IMG="ptx/mongodb:8.0.5-slim"
SCHED_IMG="ptx-edge/scheduler:1.0"
BUILDER_IMG="ptx-edge/builder:1.0"

# PTX-core components
PTX="ptx-edge"
CATALOG_IMG="ptx-sandbox/catalog:1.10.0-slim"
SANDBOX="ptx-sandbox"
CATALOG="catalog"
CATALOG_DNS="${CATALOG}.${SANDBOX}.svc.cluster.local"

# PDC
PDC=pdc
PDC_PORT=3000
PDC_NODE_PORT=30003
PDC_ID='${PDC_ID}'  # placeholder
PDC_SERVICE_KEY_BASE64_ENCODED=$(printf '%s' "${PDC_SERVICE_KEY}" | base64 -w0)
PDC_SECRET_KEY_BASE64_ENCODED=$(printf '%s' "${PDC_SECRET_KEY}" | base64 -w0)
PDC_CFG_SERVICE_KEY='${SERVICE_KEY}'  # placeholder
PDC_CFG_SECRET_KEY='${SECRET_KEY}'  # placeholder
PDC_PREFIX_TR_0="${PTX}/${PZ_TR_0}/${PDC}"
PDC_PREFIX_TR_1="${PTX}/${PZ_TR_1}/${PDC}"
PDC_PREFIX_TR_2="${PTX}/${PZ_TR_2}/${PDC}"

# REST-API
REST_API="rest-api"
API_PORT=8080
PREFIX="${PTX}/api/v1"

# Scheduler
SCHEDULER="scheduler"
SCHEDULER_METHOD="generic"
SCHEDULER_REF="${PTX}-${SCHEDULER}"

# Builder
BUILDER=builder

# Tasks
TASK1=task1
TASK2=task2
TASK3=task3