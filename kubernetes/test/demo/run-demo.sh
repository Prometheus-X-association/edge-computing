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

LOG "Execute Edge Computing (BB-02) demo..."

log "Initiate Data Processing Function without dataspace restriction"
envsubst <"rsc/builder-pvc.yaml" | ${KCOLOR} apply -f=-
envsubst <"rsc/builder-worker-uc1.yaml" | ${KCOLOR} apply -f=-
${KCOLOR} -n "${PTX}" wait --for='jsonpath={.status.phase}=Bound' --timeout="${TIMEOUT}s" "pvc/${BUILD}-pvc-${PVC}"
${KCOLOR} -n "${PTX}" wait --for="condition=Complete" --timeout="${TIMEOUT}s" "job/${BUILD}-no-pz"
echo
${KCOLOR} -n "${PTX}" get pvc,jobs -o wide
wait_enter "with Privacy Preserving"

########################################################################################################################

log "Initiate Data Processing Function with Privacy Zone restriction"
PVC=1
envsubst <"rsc/builder-pvc.yaml" | ${KCOLOR} apply --prune --all \
                                                    --prune-allowlist=core/v1/PersistentVolumeClaim -f=-
envsubst <"rsc/builder-worker-uc2.yaml" | ${KCOLOR} apply --prune --all \
                                                    --prune-allowlist=batch/v1/Job -f=-
${KCOLOR} -n "${PTX}" wait --for='jsonpath={.status.phase}=Bound' --timeout="${TIMEOUT}s" "pvc/${BUILD}-pvc-${PVC}"
${KCOLOR} -n "${PTX}" wait --for="condition=Complete" --timeout="${TIMEOUT}s" "job/${BUILD}-with-pz"
echo
${KCOLOR} -n "${PTX}" get pvc,jobs -o wide
wait_enter "with Near-Data Processing"

########################################################################################################################

log "Initiate Data Processing Function with efficient near-data processing"
PVC=2
envsubst <"rsc/builder-pvc.yaml" | ${KCOLOR} apply --prune --all \
                                                    --prune-allowlist=core/v1/PersistentVolumeClaim -f=-
envsubst <"rsc/builder-worker-uc3.yaml" | ${KCOLOR} apply --prune --all \
                                                    --prune-allowlist=batch/v1/Job -f=-
${KCOLOR} -n "${PTX}" wait --for='jsonpath={.status.phase}=Bound' --timeout="${TIMEOUT}s" "pvc/${BUILD}-pvc-${PVC}"
${KCOLOR} -n "${PTX}" wait --for="condition=Complete" --timeout="${TIMEOUT}s" "job/${BUILD}-with-ndp"
echo
${KCOLOR} -n "${PTX}" get pvc,jobs -o wide

########################################################################################################################

echo -e "\nDone."