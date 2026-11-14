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

LOG "Cluster configuration"

echo "Use local cluster setup: ${LOCAL_SETUP}"
echo "Use sandbox for PTX core: ${USE_SANDBOX}"
echo
${KCTL} config set-context --current --namespace "${PTX}"

########################################################################################################################

LOG "Installing ptx-edge from Helm chart..."
#envsubst <"${SCRIPT_DIR}/rsc/helm-values.tmp.yaml" >"${SCRIPT_DIR}/rsc/helm-values.yaml"
helm install "${PTX}" "${ROOT_DIR}/deployment/ptx-edge/" \
                --namespace="${PTX}" --create-namespace \
                -f <(envsubst <"${SCRIPT_DIR}/rsc/helm-values.tmp.yaml") \
                --set-file localRegistry.rootCAFileContent="${ROOT_DIR}/src/registry/.certs/ca/ca.crt" \
                --debug --wait --timeout="${TIMEOUT}s"

########################################################################################################################

_PDC_INSTANCES=$(kubectl get pods -l app.kubernetes.io/name=connector -o=jsonpath='{range .items[*]} | {.metadata.name}')
log "Waiting for PDC instances: ${_PDC_INSTANCES} to initialize..."
for pod in $(kubectl get pods -l app.kubernetes.io/name=connector -o jsonpath='{.items[*].metadata.name}'); do
    kubectl wait --for="condition=Initialized" --timeout="${TIMEOUT}s" "pod/${pod}"
done
#
${KCTL} wait --timeout="${TIMEOUT}s" "ds/connector" \
    --for=jsonpath='.status.numberReady'="$(kubectl get "ds/connector" -o=jsonpath='{.status.desiredNumberScheduled}')"

log "Waiting for PDC instances: $(kubectl get pods -l app.kubernetes.io/name=connector -o name) to set up..."
for pod in $(kubectl get pods -l app.kubernetes.io/name=connector -o jsonpath='{.items[*].metadata.name}'); do
    ( kubectl logs -f "pod/${pod}" -c connector --prefix & ) | timeout "${TIMEOUT}" grep -m1 "Server running on"
done

log "Waiting for PDC ingress: $(kubectl get ingress -l app.kubernetes.io/name=connector \
                                                    -o=jsonpath='{range .items[*]} | {.metadata.name}') to set up..."
sleep 10
for pz in ${DEF_ZONE}; do
    zone_pdc=$(kubectl get pods -l app.kubernetes.io/name=connector \
                                -l "privacy-zone.dataspace.ptx.org/${pz}" --no-headers --ignore-not-found)
    if [ -z "${zone_pdc}" ]; then
        warning "Missing PDC instance for zone: ${pz}"
        continue
    fi
    ${KCTL} wait --for=jsonpath='{.status.loadBalancer.ingress[].ip}' --timeout="${TIMEOUT}s" "ingress/${PDC}-${pz}"
    _PDC_URL="https://${CLUSTER_HOST}/${PTX}/${pz}/${PDC}"
    log ">>> PDC is exposed on ${_PDC_URL}"
    wget --spider -S -nv --ca-certificate="${CA_DIR}/ca.crt" \
            --retry-on-http-error=500,502 --waitretry=2 --read-timeout=3 --tries=10 "${_PDC_URL}"
    echo
    curl -LSsk --fail-with-body "${_PDC_URL}" | grep "href" | head -n1
    echo
done

########################################################################################################################

log "Waiting for API ingress:$(kubectl get ingress -l app.kubernetes.io/name=rest-api \
                                                    -o=jsonpath='{range .items[*]} | {.metadata.name}') to set up..."
sleep 10
${KCTL} wait --for=jsonpath='{.status.loadBalancer.ingress[].ip}' --timeout="${TIMEOUT}s" "ingress/rest-api"

_REST_API_URL="https://${CLUSTER_HOST}/${PREFIX}/ui/"
log ">>> rest-api is available on ${_REST_API_URL}"
wget --spider -S -nv --ca-certificate="${CA_DIR}/ca.crt" --retry-on-http-error=500,502 --waitretry=2 \
            --read-timeout=3 --tries=10 --user="${API_BASIC_USER}" --password="${API_BASIC_PASSWORD}" "${_REST_API_URL}"
curl -Ss --fail-with-body --cacert "${CA_DIR}/ca.crt" -u "${API_BASIC_USER}:${API_BASIC_PASSWORD}" \
                                                    "https://${CLUSTER_HOST}/${PREFIX}/version" | python3 -m json.tool
log ">>> rest-api is also exposed on https://${PRIMARY_HOST}/${PREFIX}/ui/\n
>>> rest-api is also exposed on https://${GW_HOST}/${PREFIX}/ui/"

########################################################################################################################

echo -e "\nDone."