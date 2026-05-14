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

########################################################################################################################

LOG "Building docker images...."

log "Remove cached cert files..."
rm -rf "${SCRIPT_DIR}/creds/cert"

log "Build PTX-edge components"
for comp in "${COMPONENTS[@]}"; do
    make -C "${ROOT_DIR}/src/${comp}" build
done

log "Cache used registry CA files locally"
mkdir -p "${SCRIPT_DIR}/creds/cert/ca" "${SCRIPT_DIR}/creds/cert/registry"
cp -vR "${ROOT_DIR}/src/registry/.certs/ca/ca.crt" "${SCRIPT_DIR}/creds/cert/ca/ca.crt"
cp -vR "${ROOT_DIR}/src/registry/.certs/ca.key" "${SCRIPT_DIR}/creds/cert/ca.key"
cp -vR "${ROOT_DIR}/src/registry/.certs/auth/server.cert" "${SCRIPT_DIR}/creds/cert/registry/server.cert"

#log "Collect federated learning images"
#for img in "${FED_COMPONENTS[@]}"; do
#    docker pull "${img}"
#done

########################################################################################################################

echo -e "\nDone."