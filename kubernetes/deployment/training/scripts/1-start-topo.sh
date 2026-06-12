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

LOG "Creating cluster infrastructure..."
k3d cluster create --config="${SCRIPT_DIR}/rsc/k3d-cluster-setup.yaml"  # k3d resolves envvars by default
${KCTL} cluster-info

log "Create Privacy Zones: zone-tr-* for <TRAINING>"
k3d --wait --timeout="${TIMEOUT}s" node create "${NODE_DATA}" --cluster="${CLUSTER}" --replicas=2 --role=agent
${KCTL} label "node/k3d-${NODE_DATA}-0" "${LAB_WORK}" "${LAB_PZ}/${PZ_DATA_0}=true" "${LAB_PDC}"
${KCTL} label "node/k3d-${NODE_DATA}-1" "${LAB_WORK}" "${LAB_PZ}/${PZ_DATA_1}=true" #"${LAB_PDC}"

log "Create Privacy Zone: ${PZ_FED} for <MANAGEMENT>"
k3d --wait --timeout="${TIMEOUT}s" node create "${NODE_FED}" --cluster="${CLUSTER}" --replicas=2 --role=agent
${KCTL} label "node/k3d-${NODE_FED}-0" "node/k3d-${NODE_FED}-1" "${LAB_WORK}" "${LAB_PZ}/${PZ_FED}=true"

#log "Reserve mount points for persistent volumes..."
#docker container ls -qf "name=k3d-node-" -f "name=k3d-demo-server-" | xargs -rI {} docker exec {} sh -c 'mkdir -pv /var/cache/storage'

log "Generate certificate for domain: ${GW_DOMAIN}"
rm -rf "${SCRIPT_DIR}/creds/cert/cluster/" && mkdir -pv "${SCRIPT_DIR}/creds/cert/cluster/"
pushd "${SCRIPT_DIR}/creds/cert/cluster/"
    ### Simple self-signed cert
    #openssl req -x509 -noenc -days 365 -newkey rsa:4096 \
    #            -subj "/C=EU/O=PTX/OU=dataspace/CN=${GW_DOMAIN}" -keyout cluster-tls.key -out cluster-tls.cert
    #envsubst <"${SCRIPT_DIR}/cfg/cluster-tls.conf" | openssl req -x509 -noenc -days 365 -new \
    #            -keyout cluster-tls.key -out cluster-tls.cert -config=-
    ### Self-signed cert with root CA
    openssl req -newkey rsa:4096 -noenc -keyout cluster-tls.key -out cluster-tls.csr \
                                -subj "/C=EU/O=PTX/OU=edge/CN=${GW_DOMAIN}" -reqexts SAN \
                                -config <(printf "[SAN]\nsubjectAltName=DNS:%s,DNS:%s" "${GW_DOMAIN}" "${LB_DOMAIN}")
    #openssl req -in cluster-tls.csr -noout -text
    openssl x509 -req -days 365 -in cluster-tls.csr -CA "${CA_DIR}/ca.crt" -CAkey "${CA_DIR}/../ca.key" \
                                -out cluster-tls.cert -CAcreateserial -extensions SAN \
                                -extfile <(printf "[SAN]\nsubjectAltName=DNS:%s,DNS:%s" "${GW_DOMAIN}" "${LB_DOMAIN}")
    openssl x509 -in cluster-tls.cert -noout -text -ext subjectAltName
    ${KCTL} -n kube-system create secret tls "${CLUSTER_TLS_SECRET}" --cert=cluster-tls.cert --key=cluster-tls.key
popd

log "Waiting for cluster networking to set up..."
${KCTL} -n kube-system wait --for="condition=Complete" --timeout="${TIMEOUT}s" job/helm-install-traefik
${KCTL} -n kube-system wait --for="condition=Available" --timeout="${TIMEOUT}s" deployment/traefik

_TRAEFIK_HTTPS="localhost:${LB_WEBSECURE_PORT}"
log "Default certificate details on ${_TRAEFIK_HTTPS}"
#sleep 3
_cntr=0
until [ -n "$(openssl s_client -brief -ignore_unexpected_eof "${_TRAEFIK_HTTPS}" </dev/null 2>&1)" ] || [ "${_cntr}" -gt 3 ];
do
    printf "." && sleep 1 && _cntr=$((_cntr+1))
done; echo
openssl s_client -showcerts -brief -CAfile="${CA_DIR}/ca.crt" -servername "${GW_DOMAIN}" "${_TRAEFIK_HTTPS}" </dev/null

LOG "Load components into registry: ${K3D_REG}"
for img in "${IMAGES[@]}"; do
    skopeo copy --dest-cert-dir="${CA_DIR}" --dest-creds="${REG_CREDS}" "docker-daemon:${img}" "docker://${K3D_REG}/${img}"
done
echo

log "Stored images in cluster"
curl -Sskf --cacert "${CA_DIR}/ca.crt" -u "${REG_CREDS}" -X GET "https://${K3D_REG}/v2/_catalog" | python3 -m json.tool

log "Created cluster nodes"
${KCTL} get nodes -L "${LAB_PZ}/${PZ_DATA_0}" -L "${LAB_PZ}/${PZ_DATA_1}" -L "${LAB_PZ}/${PZ_FED}"

log "Configured DNS entries"
${KCTL} -n kube-system get configmaps coredns -o jsonpath='{.data.NodeHosts}'

if [ "${USE_NGROK}" = "true" ] && [ -v NGROK_AUTHTOKEN ] && [ -v NGROK_DOMAIN ]; then
    log "Setup NGROK reversed HTTP proxy tunnel..."
    # Shut down running instance
    docker ps -aq -f name="ngrok-tun-*" | xargs -r docker rm --force || true
    # Run ngrok tunnel
    NGROK_CONTAINER_NAME="ngrok-tun-${LB_WEBSECURE_PORT}"
    docker run -d --net=host \
            -e NGROK_AUTHTOKEN="${NGROK_AUTHTOKEN}" \
            --name "${NGROK_CONTAINER_NAME}" \
            --label "${LAB_ROLE}=cluster" \
            ngrok/ngrok:latest \
            http "https://127.0.0.1:${LB_WEBSECURE_PORT}" --url="${NGROK_DOMAIN}" --log=stdout
    log "Waiting for completed startup..."
    # Wait for server startup
    #sleep 3
    (docker logs -t -f ngrok-tun-3000 2>&1 &) | timeout "${TIMEOUT}" grep -B5 -m1 "started tunnel" || true
    #
    if [ "$(docker container inspect -f '{{.State.Status}}' "${NGROK_CONTAINER_NAME}")" = "running" ]; then
        echo "Port: ${LB_WEBSECURE_PORT} is exposed on https://${NGROK_DOMAIN}/"
    else
        docker logs "${NGROK_CONTAINER_NAME}"
        error "NGROK container creation failed!"
        exit 1
    fi
fi

########################################################################################################################

echo -e "\nDone."