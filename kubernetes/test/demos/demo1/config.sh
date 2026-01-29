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
source "${SCRIPT_DIR}/creds/demo-cluster-creds.sh"

# Cluster
TIMEOUT=120
CLUSTER="demo"
ENV="demo"
NODE_A="node-a"
NODE_B="node-b"
NODE_AB="node-ab"

# Privacy zones
PZ_A="zone-a"
PZ_B="zone-b"

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
PDC_CFG_SERVICE_KEY='${SERVICE_KEY}'  # placeholder
PDC_CFG_SECRET_KEY='${SECRET_KEY}'  # placeholder
PDC_SERVICE_KEY_BASE64_ENCODED=$(printf '%s' "${PDC_SERVICE_KEY}" | base64 -w0)
PDC_SECRET_KEY_BASE64_ENCODED=$(printf '%s' "${PDC_SECRET_KEY}" | base64 -w0)
PDC_PREFIX_A="${PTX}/${PZ_A}/${PDC}"
PDC_PREFIX_B="${PTX}/${PZ_B}/${PDC}"

# REST-API
REST_API="rest-api"
API_PORT=8080
PREFIX="${PTX}/api/v1"

# Scheduler
SCHEDULER="scheduler"
SCHEDULER_METHOD="genetic"
SCHEDULER_REF="${PTX}-${SCHEDULER}"

# Builder
BUILDER=builder

# Tasks
TASK1=task1
TASK2=task2
TASK3=task3