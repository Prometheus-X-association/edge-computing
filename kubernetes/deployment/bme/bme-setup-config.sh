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

################################## Deploy parameters

CLUSTER="bme"

REGISTRY="registry.k3d.local"
REGISTRY_IMG="ptx-edge/registry:1.0"
REGISTRY_PORT=5000
REGISTRY_USER="admin"
REGISTRY_SECRET="admin"

K3D_REG="registry.k3d.localhost:${REGISTRY_PORT}"
CREDS="${REGISTRY_USER}:${REGISTRY_SECRET}"
CA_DIR="${PROJECT_ROOT}/src/registry/.certs/ca"
CA_CERT_PATH="/usr/share/ca-certificates/ptx-edge/registry_CA.crt"

LOADBALANCER_PORT=8888
PDC_NODEPORT=30003
PDC_ENDPOINT_PORT=3000

################################## PTX-edge setup

NAMESPACE="ptx-edge"

################################## PDC setup

source "${CFG_DIR}/.creds/bme-pdc-creds.sh"
#PDC_ENDPOINT_HOST=
#PDC_SERVICE_KEY=
#PDC_SECRET_KEY=