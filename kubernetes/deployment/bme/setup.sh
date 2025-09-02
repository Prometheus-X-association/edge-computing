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

# Load configurations
source ./config.sh

PERSIST=true

########################################################################################################################

function build() {
    echo
    echo ">>>>>>>>> Invoke ${FUNCNAME[0]}....."
    echo
    git pull || true
    for modul in ${PTX_EDGE_COMPONENTS}; do
        make -C "${PROJECT_ROOT}/src/${modul}" build
    done
	make -C "${PROJECT_ROOT}/src/ptx" build-pdc
    echo
    echo ">>> Created images:"
	docker image ls -f "reference=ptx/*" -f "reference=ptx-edge/*"
	echo
}

function init() {
    echo
    echo ">>>>>>>>> Invoke ${FUNCNAME[0]}....."
    echo
    #######
    k3d cluster create --config="${CFG_DIR}/templates/k3d-bme-cluster.yaml"
    if [ "${PERSIST}" = true ]; then
        mkdir -p ./manifests
        k3d cluster list bme -o yaml >"${CFG_DIR}/manifests/k3d-bme-cluster.yaml"
    fi
    #######
	kubectl create namespace "${DEF_NS}"
	kubectl config set-context --current --namespace "${DEF_NS}"
	kubectl cluster-info
    #######
	echo
	echo ">>> Upload images to local registry..."
	for img in ${PTX_EDGE_COMPONENTS}; do
        IMG=$(docker image ls -f reference="ptx-edge/${img}*" --format='{{.Repository}}:{{.Tag}}')
        skopeo copy --dest-cert-dir="${CA_DIR}" --dest-creds="${CREDS}" "docker-daemon:${IMG}" "docker://${K3D_REG}/${IMG}"
    done
    for img in ${PDC_COMPONENTS}; do
		IMG=$(docker image ls -f reference="ptx/${img}*" --format='{{.Repository}}:{{.Tag}}')
		skopeo copy --dest-cert-dir="${CA_DIR}" --dest-creds="${CREDS}" "docker-daemon:${IMG}" "docker://${K3D_REG}/${IMG}"
	done
	#######
    echo
	echo ">>> Uploaded images:"
	curl -Sskf --cacert "${CA_DIR}/ca.crt" -u "${CREDS}" -X GET "https://${K3D_REG}/v2/_catalog" | python3 -m json.tool
	echo
}

function remove() {
    echo
    echo ">>>>>>>>> Invoke ${FUNCNAME[0]}....."
    echo
    k3d cluster list "${CLUSTER}" || cluster_missing="$?"
    if [ ! "${cluster_missing+0}" ]; then
            kubectl delete namespace "${DEF_NS}" --ignore-not-found --now || true
    fi
    rm -rf manifests/
}


function cleanup() {
    remove
    echo
    echo ">>>>>>>>> Invoke ${FUNCNAME[0]}....."
    echo
    k3d cluster delete "${CLUSTER}" || true
    sudo rm -rf "${CFG_DIR}/.cache"
    docker image ls -qf "reference=ptx/*" -f "reference=ptx-edge/*" | xargs -r docker rmi -f
	docker image prune -f
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
	kubectl logs --ignore-errors ds/pdc
}

########################################################################################################################

function deploy() {
    echo
    echo ">>>>>>>>> Invoke ${FUNCNAME[0]}....."
    echo
    kubectl get ns "${DEF_NS}" || (
        kubectl create namespace "${DEF_NS}" && kubectl config set-context --current --namespace "${DEF_NS}")
    echo
    #######
    if [ "${PERSIST}" = true ]; then
        echo
        echo ">>> Generate manifests...."
        mkdir -p ./manifests
        pushd templates >/dev/null
        for file in ptx-*.yaml; do
            echo "Reading ${file}..."
            envsubst <"${CFG_DIR}/templates/${file}" >"${CFG_DIR}/manifests/${file}"
            echo "  -> Generated manifest: ${CFG_DIR}/manifests/${file}"
        done
        popd >/dev/null
    fi
    #######
	echo
	echo "Waiting for traefik to be installed..."
    kubectl -n kube-system wait --for="condition=Complete" --timeout="${TIMEOUT}" job/helm-install-traefik-crd
    kubectl -n kube-system wait --for="condition=Complete" --timeout="${TIMEOUT}" job/helm-install-traefik
    kubectl -n kube-system wait --for="condition=Available" --timeout="${TIMEOUT}" deployment/traefik
    #######
    echo
    echo ">>> Applying ptx-pdc-daemon.yaml"
    if [ "${PERSIST}" = true ]; then
        kubectl apply -f="${CFG_DIR}/manifests/ptx-pdc-daemon.yaml"
    else
        envsubst <"${CFG_DIR}/templates/ptx-pdc-daemon.yaml" | kubectl apply -f=-
    fi
	kubectl wait --for=jsonpath='.status.numberReady'=1 --timeout="${TIMEOUT}" daemonset/pdc
	kubectl wait --for=jsonpath='{.spec.clusterIP}' --timeout="${TIMEOUT}" services -l app=pdc
	echo "Waiting for PDC to set up..."
	for pod in $(kubectl get pods -l app=pdc -o jsonpath='{.items[*].metadata.name}'); do
		( kubectl logs -f pod/"${pod}" -c connector & ) | timeout "${TIMEOUT}" grep -m1 "Server running on"
	done
	#######
	echo
	echo "Generate TLS..."
	rm -rf "${CFG_DIR}"/.creds/api && mkdir -p "${CFG_DIR}"/.creds/api
	openssl req -x509 -noenc -days 365 -newkey rsa:2048 \
			-CA "${PROJECT_ROOT}"/src/registry/.certs/ca/ca.crt -CAkey "${PROJECT_ROOT}"/src/registry/.certs/ca.key \
			-subj "/C=EU/ST=''/L=''/O=PTX/OU=dataspace/CN=api.ptx-edge.localhost" \
			-keyout "${CFG_DIR}"/.creds/api/tls.key -out "${CFG_DIR}"/.creds/api/tls.cert
	kubectl create secret tls api-tls --cert="${CFG_DIR}"/.creds/api/tls.cert --key="${CFG_DIR}"/.creds/api/tls.key
	#######
    echo
    echo ">>> Applying ptx-pdc-ingress.yaml"
    if [ "${PERSIST}" = true ]; then
        kubectl apply -f="${CFG_DIR}/manifests/ptx-pdc-ingress.yaml"
    else
        envsubst <"${CFG_DIR}/templates/ptx-pdc-ingress.yaml" | kubectl apply -f=-
    fi
    echo
    echo "Check http://localhost:8888/ptx-edge/zone-0/pdc/..."
    wget -T5 --retry-on-http-error=404,502 --tries=5 --read-timeout=5 -O /dev/null -S http://localhost:8888/ptx-edge/zone-0/pdc/
    #######
    echo
    echo ">>> Applying ptx-rest-api-deployment.yaml"
    if [ "${PERSIST}" = true ]; then
        kubectl apply -f="${CFG_DIR}/manifests/ptx-rest-api-deployment.yaml"
    else
        envsubst <"${CFG_DIR}/templates/ptx-rest-api-deployment.yaml" | kubectl apply -f=-
    fi
    kubectl wait --for="condition=Available" --timeout="${TIMEOUT}" deployment/api
    #######
    echo
    echo ">>> Applying ptx-rest-api-ingress.yaml"
    if [ "${PERSIST}" = true ]; then
        kubectl apply -f="${CFG_DIR}/manifests/ptx-rest-api-ingress.yaml"
    else
        envsubst <"${CFG_DIR}/templates/ptx-rest-api-ingress.yaml" | kubectl apply -f=-
    fi
    echo
    echo "Check http://localhost:8888/ptx-edge/api/v1/versions..."
    wget -T5 --retry-on-http-error=404,502 --tries=5 --read-timeout=5 -O /dev/null -S http://localhost:8888/ptx-edge/api/v1/versions
    #######
    echo
    echo ">>> Applying ptx-scheduler-deployment.yaml"
    if [ "${PERSIST}" = true ]; then
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
    -p  Persist generated manifests.
    -t  Set global timeout parameter (def: ${TIMEOUT})
    -h  Display help.
EOF
}

while getopts ":t:phcbidrs" flag; do
	case "${flag}" in
        p)
            echo "[x] Manifests will be persisted."
            PERSIST=true
            ;;
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
echo

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