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

# shellcheck disable=SC2155
export CFG_DIR=$(readlink -f "$(dirname "$0")")
# shellcheck disable=SC2155
export PROJECT_ROOT=$(readlink -f "${CFG_DIR}/../..")

# Load configurations
source "${CFG_DIR}/config.sh"
COMMENT_FILTER='/^[[:blank:]]*#/d;s/[[:blank:]]*#.*//'

# Global settings
PERSIST=true
RESET=true

########################################################################################################################

function build() {
    echo
    echo ">>>>>>>>> Invoke ${FUNCNAME[0]}....."
    echo
    if [ "${RESET}" = "true" ]; then
        git pull || true
        for modul in ${PTX_EDGE_COMPONENTS}; do
            make -C "${PROJECT_ROOT}/src/${modul}" build
        done
        make -C "${PROJECT_ROOT}/src/ptx" build-pdc
        echo
        echo ">>> Created images:"
        docker image ls -f "reference=ptx/*" -f "reference=ptx-edge/*"
        echo
    else
        echo
        echo ">>> Skip image building [RESET=${RESET}]"
        echo
    fi
}

function init() {
    echo
    echo ">>>>>>>>> Invoke ${FUNCNAME[0]}....."
    echo
    #######
    if [ "${PERSIST}" = "true" ]; then
        echo
        echo ">>> Generate manifests...."
        mkdir -pv "${CFG_DIR}/manifests"
        pushd "${CFG_DIR}/templates" >/dev/null
        for file in k3d-*.yaml; do
            echo "Reading ${file}..."
            envsubst <"${CFG_DIR}/templates/${file}" | sed "${COMMENT_FILTER}" >"${CFG_DIR}/manifests/${file}"
            echo "  -> Generated manifest: ${CFG_DIR}/manifests/${file}"
            echo
        done
        popd >/dev/null
    fi
    #mkdir -pv "${CFG_DIR}/.cache/pvc"
    k3d cluster create --config="${CFG_DIR}/manifests/k3d-bme-cluster.yaml"
    #######
	kubectl create namespace "${PTX_NS}"
	kubectl config set-context --current --namespace "${PTX_NS}"
	kubectl cluster-info
    #######
    if [ "${RESET}" = "true" ]; then
        echo
        echo ">>> Upload images to local registry..."
        for img in ${PTX_EDGE_COMPONENTS}; do
            IMG=$(docker image ls -f reference="ptx-edge/${img}*" --format='{{.Repository}}:{{.Tag}}')
            skopeo copy --dest-cert-dir="${REG_CA_DIR}" --dest-creds="${REG_CREDS}" \
                        "docker-daemon:${IMG}" "docker://${K3D_REG}/${IMG}"
        done
        for img in ${PDC_COMPONENTS}; do
            IMG=$(docker image ls -f reference="ptx/${img}*" --format='{{.Repository}}:{{.Tag}}')
            skopeo copy --dest-cert-dir="${REG_CA_DIR}" --dest-creds="${REG_CREDS}" \
                        "docker-daemon:${IMG}" "docker://${K3D_REG}/${IMG}"
        done
    else
        echo
        echo ">>> Skip image uploading [RESET=${RESET}]"
        echo
    fi
	#######
    echo
	echo ">>> Uploaded images:"
	curl -Sskf --cacert "${REG_CA_DIR}/ca.crt" -u "${REG_CREDS}" -X GET "https://${K3D_REG}/v2/_catalog" | python3 -m json.tool
	echo
}

function remove() {
    echo
    echo ">>>>>>>>> Invoke ${FUNCNAME[0]}....."
    echo
    k3d cluster list "${CLUSTER}" || cluster_missing="$?"
    if [ ! "${cluster_missing+0}" ]; then
            kubectl delete namespace "${PTX_NS}" --ignore-not-found --now || true
    fi
    rm -rf "${CFG_DIR}/manifests/" "${CFG_DIR}/.creds/gw/"
}


function cleanup() {
    remove
    echo
    echo ">>>>>>>>> Invoke ${FUNCNAME[0]}....."
    echo
    k3d cluster delete "${CLUSTER}" || true
    if [ "${RESET}" = "true" ]; then
        sudo rm -rf "${CFG_DIR}/.cache"
        docker image ls -qf "reference=ptx/*" -f "reference=ptx-edge/*" | xargs -r docker rmi -f
        docker image prune -f
    else
        echo
        echo ">>> Skip image purge [RESET=${RESET}]"
        echo
    fi
}


function status() {
    echo
    echo ">>>>>>>>> Cluster[${CLUSTER}] deployment status:"
    echo
    k3d cluster list --no-headers | grep -q ^ # check for existing cluster
	kubectl get --ignore-not-found \
	    all,endpointslices,configmaps,secrets,ingress,ingressroutes.traefik.io,middlewares.traefik.io -o wide
	echo
	kubectl get --ignore-not-found events
	echo
	kubectl logs --ignore-errors ds/"${PDC}"
}

########################################################################################################################

function deploy() {
    echo
    echo ">>>>>>>>> Invoke ${FUNCNAME[0]}....."
    echo
    kubectl get ns "${PTX_NS}" || (
        kubectl create namespace "${PTX_NS}" && kubectl config set-context --current --namespace "${PTX_NS}")
    echo
    #######
    if [ "${PERSIST}" = "true" ]; then
        echo
        echo ">>> Generate manifests...."
        mkdir -pv "${CFG_DIR}/manifests"
        pushd "${CFG_DIR}/templates" >/dev/null
        for file in ptx-*.yaml; do
            echo "Reading ${file}..."
            envsubst <"${CFG_DIR}/templates/${file}" | sed "${COMMENT_FILTER}" >"${CFG_DIR}/manifests/${file}"
            echo "  -> Generated manifest: ${CFG_DIR}/manifests/${file}"
            echo
        done
        popd >/dev/null
    fi
    #######
	echo
	echo ">>> Generate TLS..."
	rm -rf "${CFG_DIR}/.creds/gw/" && mkdir -pv "${CFG_DIR}/.creds/gw/"
    pushd "${CFG_DIR}/.creds/gw/" >/dev/null
    ### Simple self-signed cert
 	# openssl req -x509 -noenc -days 365 -newkey rsa:2048 -subj "/C=EU/O=PTX/OU=dataspace/CN=${GW_TLS_DOMAIN}" \
    #            -keyout tls.key -out tls.cert
    ### Simple self-signed cert with specific CA
	# openssl req -x509 -noenc -days 365 -newkey rsa:2048 \
	# 		-CA "${PROJECT_ROOT}"/src/registry/.certs/ca/ca.crt -CAkey "${PROJECT_ROOT}"/src/registry/.certs/ca.key \
	#		-subj "/C=EU/O=PTX/OU=dataspace/CN=${GW_TLS_DOMAIN}" -keyout tls.key -out tls.cert
    ### Self-signed cert with CA and SAN
    #openssl req -newkey rsa:2048 -noenc -keyout tls.key -out tls.csr \
    #        -subj "/C=EU/O=PTX/OU=dataspace/CN=${GW_TLS_DOMAIN}"
    #printf "subjectAltName=DNS:%s" "${GW_LOCAL_DOMAIN}" | openssl x509 -req -days 365 -extfile=- \
    #        -CA "${PROJECT_ROOT}/src/registry/.certs/ca/ca.crt" \
    #        -CAkey "${PROJECT_ROOT}/src/registry/.certs/ca.key" -in tls.csr -out tls.cert
	### Self-signed cert from .conf
    if [ "${PERSIST}" = true ]; then
        echo
        echo ">>> Generate manifests...."
        mkdir -pv "${CFG_DIR}/manifests"
        pushd "${CFG_DIR}/templates" >/dev/null
        for file in *.conf; do
            echo "Reading ${file}..."
            envsubst <"${CFG_DIR}/templates/${file}" | sed "${COMMENT_FILTER}" >"${CFG_DIR}/manifests/${file}"
            echo "  -> Generated config: ${CFG_DIR}/manifests/${file}"
        done
        popd >/dev/null
    fi
    openssl req -new -x509 -noenc -days 365 -config "${CFG_DIR}/manifests/openssl.conf" -keyout tls.key -out tls.cert
	#######
	kubectl -n kube-system create secret tls gw-tls --cert=tls.cert --key=tls.key
	popd >/dev/null
    #######
	echo
	echo "Waiting for traefik to be installed..."
    kubectl -n kube-system wait --for="condition=Complete" --timeout="${TIMEOUT}" job/helm-install-traefik
    kubectl -n kube-system wait --for="condition=Available" --timeout="${TIMEOUT}" deployment/traefik
	#######
    echo
    echo ">>> Applying ptx-pdc-daemon.yaml"
    if [ "${PERSIST}" = "true" ]; then
        kubectl apply -f="${CFG_DIR}/manifests/ptx-pdc-daemon.yaml"
    else
        envsubst <"${CFG_DIR}/templates/ptx-pdc-daemon.yaml" | kubectl apply -f=-
    fi
	kubectl wait --for=jsonpath='.status.numberReady'=1 --timeout="${TIMEOUT}" daemonset/"${PDC}"
	kubectl wait --for=jsonpath='{.spec.clusterIP}' --timeout="${TIMEOUT}" services -l app="${PDC}"
	echo "Waiting for PDC to set up..."
	for pod in $(kubectl get pods -l app="${PDC}" -o jsonpath='{.items[*].metadata.name}'); do
		( kubectl logs -f pod/"${pod}" -c connector & ) | timeout "${TIMEOUT}" grep -m1 "Server running on"
	done
	#######
    echo
    echo ">>> Applying ptx-pdc-ingress.yaml"
    if [ "${PERSIST}" = "true" ]; then
        kubectl apply -f="${CFG_DIR}/manifests/ptx-pdc-ingress.yaml"
    else
        envsubst <"${CFG_DIR}/templates/ptx-pdc-ingress.yaml" | kubectl apply -f=-
    fi
    CHECK_PDC_URL="https://${GW_LOCAL_DOMAIN}:${GW_WEBSECURE_PORT}/${PDC_SUBPATH}/"
    echo
    echo "Check ${CHECK_PDC_URL}..."
    wget -S -T5 --retry-on-http-error=404,502 --tries=5 --read-timeout=5 -O /dev/null --no-check-certificate "${CHECK_PDC_URL}"
    curl -Ssfk "${CHECK_PDC_URL}" | grep "href"
    ###
    CHECK_PDC_URL="https://${GW_TLS_DOMAIN}:${GW_WEBSECURE_PORT}/${PDC_SUBPATH}/"
    echo
    echo "Check ${CHECK_PDC_URL}..."
    curl -Ssfk -I "${CHECK_PDC_URL}" || true
    #######
    echo
    echo ">>> Applying ptx-rest-api-deployment.yaml"
    if [ "${PERSIST}" = "true" ]; then
        kubectl apply -f="${CFG_DIR}/manifests/ptx-rest-api-deployment.yaml"
    else
        envsubst <"${CFG_DIR}/templates/ptx-rest-api-deployment.yaml" | kubectl apply -f=-
    fi
    kubectl wait --for="condition=Available" --timeout="${TIMEOUT}" deployment/"${API}"
    #######
    echo
    echo ">>> Applying ptx-rest-api-ingress.yaml"
    if [ "${PERSIST}" = "true" ]; then
        kubectl apply -f="${CFG_DIR}/manifests/ptx-rest-api-ingress.yaml"
    else
        envsubst <"${CFG_DIR}/templates/ptx-rest-api-ingress.yaml" | kubectl apply -f=-
    fi
    CHECK_API_URL="https://${GW_LOCAL_DOMAIN}:${GW_WEBSECURE_PORT}/${API_SUBPATH}/versions"
    echo
    echo "Check ${CHECK_API_URL}..."
    wget -S -T5 --retry-on-http-error=404,502 --tries=5 --read-timeout=5 -O /dev/null --no-check-certificate \
            --user="${API_BASIC_USER}" --password="${API_BASIC_PASSWORD}" "${CHECK_API_URL}"
    curl -Ssfk -u "${API_BASIC_USER}:${API_BASIC_PASSWORD}" "${CHECK_API_URL}" | python3 -m json.tool
    ###
    CHECK_API_URL="https://${GW_TLS_DOMAIN}:${GW_WEBSECURE_PORT}/${API_SUBPATH}/versions"
    echo
    echo "Check ${CHECK_API_URL}..."
    curl -Ssfk -I -u "${API_BASIC_USER}:${API_BASIC_PASSWORD}" "${CHECK_API_URL}"
    #######
    echo
    echo ">>> Applying ptx-scheduler-deployment.yaml"
    if [ "${PERSIST}" = "true" ]; then
        kubectl apply -f="${CFG_DIR}/manifests/ptx-scheduler-deployment.yaml"
    else
        envsubst <"${CFG_DIR}/templates/ptx-scheduler-deployment.yaml" | kubectl apply -f=-
    fi
    kubectl wait --for="condition=Available" --timeout="${TIMEOUT}" deployment/"${SCHEDULER}"
}

########################################################################################################################

function display_help() {
    cat <<EOF
Usage: $0 [options]

Options:
    -c  Only perform cleanup.
    -b  Only perform build.
    -i  Only perform init.
    -d  Only perform deploy.
    -r  Only perform remove.
    -s  Only perform status.
    -p  Do not persist generated manifests.
    -x  Redeploy cluster without build/cleanup.
    -t  Set global timeout parameter (def: ${TIMEOUT})
    -h  Display help.
EOF
}

while getopts ":t:hcbidrspx" flag; do
	case "${flag}" in
        c)
            cleanup
            exit 0
            ;;
        b)
            build
            exit 0
            ;;
        i)
            init
            exit 0
            ;;
        d)
            deploy
            status
            exit 0
            ;;
        r)
            remove
            status
            exit 0
            ;;
        s)
            status
            exit 0
            ;;
        p)
            echo "[x] Manifests will NOT be persisted."
            PERSIST="false"
            ;;
        x)
            echo "[x] Image build/cleanup deactivated."
            RESET="false"
            ;;
        t)
            TIMEOUT=${OPTARG}
            echo "Global timeout set to ${TIMEOUT}"
            ;;
        h)
            display_help
            exit 2
            ;;
        ?)
            echo "Invalid parameter: -${OPTARG} !"
            exit 1
            ;;
    esac
done

########################################################################################################################

echo
echo "Start deployment of cluster: ${CLUSTER}"
echo  " > PERSIST=${PERSIST}"
echo  " > RESET=${RESET}"

########################################################################################################################

cleanup
build
init
deploy
status

########################################################################################################################

echo
echo "Cluster: ${CLUSTER} deployed."
echo