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

source "$(readlink -f "$(dirname "$0")/../cfg/config.sh")"

DVA_BB_REPO="git@github.com:Prometheus-X-association/data-veracity.git"
DVA_BB_DIR="dva"
DVA_BB_VER="remotes/origin/edge-node-demo"
FORCE_RECREATE="true"

########################################################################################################################

LOG "Building docker images..."

log "Remove cached cert files..."
rm -rfv "${SCRIPT_DIR}/creds/cert"

log "Build PTX-edge components"
for comp in "${COMPONENTS[@]}"; do
    log "Building ${comp}..."
    make -C "${ROOT_DIR}/src/${comp}" build
done

log "Cache used registry CA files locally..."
mkdir -p "${SCRIPT_DIR}/creds/cert/ca" "${SCRIPT_DIR}/creds/cert/registry"
cp -vR "${ROOT_DIR}/src/registry/.certs/ca/ca.crt" "${SCRIPT_DIR}/creds/cert/ca/ca.crt"
cp -vR "${ROOT_DIR}/src/registry/.certs/ca.key" "${SCRIPT_DIR}/creds/cert/ca.key"
cp -vR "${ROOT_DIR}/src/registry/.certs/auth/server.cert" "${SCRIPT_DIR}/creds/cert/registry/server.cert"

log "Update PtxEdgeWorker CRD..."
cp -vR "${ROOT_DIR}/src/controller/crd/ptx-edge-worker.yaml" "${SCRIPT_DIR}/rsc/ptx-edge-worker-crd.yaml"

########################################################################################################################

#log "Collect federated learning images"
#for img in "${FED_COMPONENTS[@]}"; do
#    docker pull "${img}"
#done

log "Build DVA components..."

if [ -z "${DVA_BB_DIR:-}" ]; then
    DVA_BB_DIR=$(readlink -f "$(dirname "$0")/dva")
fi
mkdir -p "${DVA_BB_DIR}"
echo "Used dir for DVA: ${DVA_BB_DIR}"
echo "Used version for DVA: ${DVA_BB_VER:=main}"

if [ "${FORCE_RECREATE}" = "true" ] || [ ! -d "${DVA_BB_DIR}" ] || [ -z "$( ls -A "${DVA_BB_DIR}" )" ]; then
    log "Cleanup DVA config..."
    rm -rf "${DVA_BB_DIR}"

    log "Pull DVA source with version: ${DVA_BB_VER}..."
    git clone "${DVA_BB_REPO}" "${DVA_BB_DIR}"
    pushd "${DVA_BB_DIR}"
        git switch -C "build-${DVA_BB_VER}" --no-track "${DVA_BB_VER}"
    popd
fi

log "Build DVA images..."
pushd "${DVA_BB_DIR}/test-env"
    docker compose -p "dva" build
popd
docker image ls --filter "label=com.docker.compose.project=dva"

########################################################################################################################

echo -e "\nDone."