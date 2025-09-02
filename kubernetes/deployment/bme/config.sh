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
set -o allexport

CFG_DIR=$(readlink -f "$(dirname "$0")")
PROJECT_ROOT=$(readlink -f "${CFG_DIR}/../..")

TIMEOUT=120s

################################## Build parameters

PTX_EDGE_COMPONENTS="builder rest-api scheduler registry"
PDC_COMPONENTS="connector mongodb"

################################## Cluster parameters

CLUSTER="bme"

REGISTRY_HOST="registry.k3d.local"
REGISTRY_PORT=5000
REGISTRY="${REGISTRY_HOST}:${REGISTRY_PORT}"

REGISTRY_IMG="ptx-edge/registry:1.0"

REGISTRY_USER="admin"
REGISTRY_SECRET="admin"
CREDS="${REGISTRY_USER}:${REGISTRY_SECRET}"

K3D_REG="registry.k3d.localhost:${REGISTRY_PORT}"
CA_DIR="${PROJECT_ROOT}/src/registry/.certs/ca"
CA_CERT_PATH="/usr/share/ca-certificates/ptx-edge/registry_CA.crt"

LOADBALANCER_PORT=8888
PDC_NODEPORT=30003
PDC_DEF_PORT=3000

################################## PTX-edge setup

DEF_NS="ptx-edge"
DEF_ZONE="zone-0"

################################## PDC setup

PDC="pdc"

source "${CFG_DIR}/.creds/bme-pdc-creds.sh"
#CLUSTER_GW=
#SERVICE_KEY=
#SECRET_KEY=
PDC_ENDPOINT="http://${CLUSTER_GW}:${LOADBALANCER_PORT}/${DEF_NS}/${DEF_ZONE}/${PDC}"
PDC_SERVICE_KEY_BASE64_ENCODED=$(printf '%s' "${SERVICE_KEY}" | base64 -w0)
PDC_SECRET_KEY_BASE64_ENCODED=$(printf '%s' "${SECRET_KEY}" | base64 -w0)
PDC_SERVICE_KEY='${PDC_SERVICE_KEY}'    # Placeholder for substitution in endpoint.sh
PDC_SECRET_KEY='${PDC_SECRET_KEY}'      # Placeholder for substitution in endpoint.sh

#SESSION_SECRET=$(LC_ALL=C tr -dc A-Za-z0-9 </dev/urandom | head -c 16)
SESSION_SECRET=$(openssl rand -base64 32 | tr -d /=+ | cut -c -16)    # Autogenerate

PTX_CONTRACT_URI="https://contract.visionstrust.com/"
PTX_CATALOG_URI="https://api.visionstrust.com/v1/"
PTX_CONSENT_URI="https://consent.visionstrust.com/v1"

################################## REST-API setup

API="api"
API_VER="v1"
API_PORT=8080

################################## Scheduler setup

SCHEDULER="scheduler"
SCHEDULER_METHOD="random"
SCHEDULER_REF="${DEF_NS}-${SCHEDULER}"