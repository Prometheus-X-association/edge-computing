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

LOG "Execute Privacy Preserving use case..."

log "Initiate Data Processing Function without PTX-edge provision"
envsubst <"rsc/builder-pvc.yaml" | kubectl apply -f=-
echo
kubectl -n "${PTX}" get pvc
envsubst <"rsc/builder-worker.yaml" | kubectl apply -f=-
kubectl -n "${PTX}" wait --for='jsonpath={.status.phase}=Bound' --timeout="${TIMEOUT}s" "pvc/${BUILD}-pvc"
kubectl -n "${PTX}" wait --for="condition=Complete" --timeout="${TIMEOUT}s" "job/${BUILD}-no-pz"
echo
kubectl -n "${PTX}" get jobs -o wide
echo
read -rp "### Press ENTER to continue..."

log "Initiate Data Processing Function based on Privacy Zone restriction"
envsubst <"rsc/builder-worker.yaml" | kubectl delete -f=-
envsubst <"rsc/builder-pvc-pz.yaml" | kubectl apply -f=-
envsubst <"rsc/builder-worker-pz.yaml" | kubectl apply -f=-
kubectl -n "${PTX}" wait --for='jsonpath={.status.phase}=Bound' --timeout="${TIMEOUT}s" "pvc/${BUILD}-pvc"
kubectl -n "${PTX}" wait --for="condition=Complete" --timeout="${TIMEOUT}s" "job/${BUILD}-with-pz"
echo
kubectl -n "${PTX}" get jobs -o wide

########################################################################################################################

echo -e "\nDone."