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
SCRIPTS_DIR=$(readlink -f "$(dirname "$0")")
ROOT_DIR=$(readlink -f "$(dirname "$0")/../..")
source "${SCRIPTS_DIR}/../scripts/helper.sh"
if command -v kubecolor >/dev/null 2>&1; then
    KUBECOLOR_FORCE_COLORS=auto
    KUBECOLOR_PRESET="dark"
    KCOLOR=kubecolor
else
    KCOLOR=kubectl
fi

# Cluster
TIMEOUT=60
CLUSTER=demo
NODE_A=node-a
NODE_B=node-b
NODE_AB=node-ab

# Privacy zones
PZ_A=zone-A
PZ_B=zone-B

# PTX-edge components
API_IMG=ptx-edge/rest-api:1.0
BUILD_IMG=ptx-edge/builder:1.0
PDC_IMG=ptx/connector:1.9.10-slim
MONGODB_IMG=ptx/mongodb:8.0.5-slim

# REST-API
PTX=ptx-edge
REST_API=rest-api
API_PORT=8080
PREFIX=ptx-edge/v1

# PDC
PDC=pdc
PDC_PORT=3000
PDC_NODE_PORT=30003
PDC_PREFIX=ptx-edge/pdc

# Builder
BUILD=builder
PVC=0

# Worker
WORKER_IMG=busybox:latest