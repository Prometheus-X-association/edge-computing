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

# Config --------------------------------------------------------------------------------

# Dependencies
DEPS=(docker k3d kubectl helm kubecolor)

DOCKER_VER=29.2.0
K3D_VER=v5.8.3
KUBECTL_VER=v1.31.5	# used by k3d v5.8.3 / k3s v1.31.5
HELM_VER=v4.0.0
SKOPEO_VER=v1.21.0

PKG_FREEZE=false
NO_CHECK=false
SLIM_SETUP=false
UPDATE=false
INIT_CLEANUP=false
NO_DOCKER=false

GRP_DOCKER="docker"
CHECK_IMG="hello-world:latest"
TEST_K8S='test-cluster'
TEST_NS='ptx-edge'
TEST_ID='test42'
TEST_IMG='k8s.gcr.io/pause'
TEST_CMD=''
TEST_OK='Running'

PZ_LAB='privacy-zone.dataspace.ptx.org'
RET_VAL=0

# Install actions --------------------------------------------------------------------------------

function install_deps() {
    echo -e "\n>>> Install dependencies...\n"
    sudo apt-get update && sudo apt-get install -y ca-certificates apt-transport-https wget curl gettext \
                                                     make bash-completion apache2-utils
}

function install_docker() {
    if command -v docker >/dev/null 2>&1 && [ ${UPDATE} = true ]; then
        printf "\n>>> Remove previous %s...\n" "$(docker -v)"
        sudo systemctl stop docker
        sudo apt-mark unhold docker-ce docker-ce-cli docker-ce-rootless-extras
        sudo apt-get remove -y --allow-change-held-packages docker-ce docker-ce-cli containerd.io \
                            docker-compose-plugin docker-ce-rootless-extras docker-buildx-plugin docker-model-plugin
    fi
    echo -e "\n>>> Install Docker[${DOCKER_VER}]...\n"
    curl -fsSL https://get.docker.com/ | VERSION=${DOCKER_VER} sh
    if [ ${PKG_FREEZE} = true ]; then
        echo -e "\n>>> Freeze Docker[${DOCKER_VER}]...\n"
        sudo apt-mark hold docker-ce docker-ce-cli docker-ce-rootless-extras
    fi
    # Privileged Docker
    sudo usermod -aG "${GRP_DOCKER}" "${USER}"
    echo
    (set -x; docker --version)
}

function install_k3d() {
    echo -e "\n>>> Install k3d binary[${K3D_VER}]...\n"
    curl -fsSL https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | TAG=${K3D_VER} bash
    echo
    (set -x; k3d version)
}

function install_kubectl() {
    echo -e "\n>>> Install kubectl binary[${KUBECTL_VER}]...\n"
    curl -fsSL -O "https://dl.k8s.io/release/${KUBECTL_VER}/bin/linux/amd64/kubectl" && \
        sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl && rm kubectl
    echo
    (set -x; kubectl version --client)
}

function install_kubecolor() {
    KCOLOR_VER="$(wget -q -O- https://kubecolor.github.io/packages/deb/version)_$(dpkg --print-architecture)"
    echo -e "\n>>> Install kubecolor binary[${KCOLOR_VER}]...\n"
    curl -fsSL -O "https://kubecolor.github.io/packages/deb/pool/main/k/kubecolor/kubecolor_${KCOLOR_VER}.deb" && \
        sudo dpkg -i "kubecolor_${KCOLOR_VER}.deb" && rm "kubecolor_${KCOLOR_VER}.deb"
    (set -x; kubectl version --client)
}

function install_helm() {
    echo -e "\n>>> Install Helm binary[${HELM_VER}]...\n"
    curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | TAG=${HELM_VER} bash
    echo
    (set -x; helm version --short)
}

function install_skopeo() {
    echo -e "\n>>> Install skopeo binary[${SKOPEO_VER}]...\n"
    # sudo apt-get update && sudo apt-get install -y skopeo   # skopeo version 1.13.3
    sudo add-apt-repository -ny ppa:longsleep/golang-backports
    # sudo apt-get satisfy "golang (>=1.23)" go-md2man
    sudo apt-get update && sudo apt-get install -y libgpgme-dev libassuan-dev libbtrfs-dev pkg-config go-md2man golang
    TMP_DIR=$(mktemp -d) && pushd "${TMP_DIR}"
        git clone https://github.com/containers/skopeo && cd skopeo
        git switch --detach ${SKOPEO_VER}
        make bin/skopeo docs
        sudo install -o root -g root -m 0755 bin/skopeo /usr/local/bin/skopeo
        sudo mkdir -p /usr/local/share/man/man1
        sudo install -m 644 docs/*.1 /usr/local/share/man/man1
    popd
    rm -rf "${TMP_DIR}"
    echo
    (set -x; skopeo --version)
}

function setup_k3d_bash_completion() {
    echo -e "\n>>> Install k3d bash completion...\n"
    mkdir -p /etc/bash_completion.d
    k3d completion bash | sudo tee /etc/bash_completion.d/k3d > /dev/null
    sudo chmod a+r /etc/bash_completion.d/k3d
    source ~/.bashrc
    echo "Finished."
}

function setup_kubectl_bash_completion() {
    echo -e "\n>>> Install Kubectl bash completion...\n"
    mkdir -p /etc/bash_completion.d
    kubectl completion bash | sudo tee /etc/bash_completion.d/kubectl > /dev/null
    sudo chmod a+r /etc/bash_completion.d/kubectl
    source ~/.bashrc
    echo "Finished."
}

function setup_helm_bash_completion() {
    echo -e "\n>>> Install Helm bash completion...\n"
    mkdir -p /etc/bash_completion.d
    helm completion bash | sudo tee /etc/bash_completion.d/helm > /dev/null
    sudo chmod a+r /etc/bash_completion.d/helm
    source ~/.bashrc
    echo "Finished."
}

function setup_skopeo_bash_completion() {
    echo -e "\n>>> Install Skopeo bash completion...\n"
    mkdir -p /etc/bash_completion.d
    skopeo completion bash | sudo tee /etc/bash_completion.d/skopeo > /dev/null
    sudo chmod a+r /etc/bash_completion.d/skopeo
    source ~/.bashrc
    echo "Finished."
}

# Test actions --------------------------------------------------------------------------------

function setup_test_cluster() {
    echo -e "\n>>> Prepare test cluster with id: ${TEST_K8S}...\n"
#    k3d cluster create "$TEST_K8S" --wait --timeout=30s --servers=1 --agents=2 \
#        --k3s-node-label="$PZ_LAB/zone-C=true@server:0" \
#        --k3s-node-label="$PZ_LAB/zone-A=true@agent:0" \
#        --k3s-node-label="$PZ_LAB/zone-B=true@agent:*"
    cat <<EOF | k3d cluster create "${TEST_K8S}" --wait --timeout=60s --config=-
kind: Simple
apiVersion: k3d.io/v1alpha5
metadata:
  name: ${TEST_K8S}
servers: 1
agents: 2
options:
  k3d:
    wait: true
    timeout: "30s"
  k3s:
    nodeLabels:
      - label: "${PZ_LAB}/zone-C=true"
        nodeFilters:
          - server:0
      - label: "${PZ_LAB}/zone-A=true"
        nodeFilters:
          - agent:0
      - label: "${PZ_LAB/}zone-B=true"
        nodeFilters:
          - agent:*
EOF
    echo -e "\n>>> K3d cluster info:\n"
    kubectl cluster-info --context k3d-${TEST_K8S}
    echo -e "\n>>> K3s setup:\n"
    kubectl version
    echo
    kubectl -n kube-system get all
    echo -e "\n>>> K3s nodes:\n"
    kubectl get nodes -o wide -L ${PZ_LAB}/zone-A -L ${PZ_LAB}/zone-B -L ${PZ_LAB}/zone-C
}

function perform_test_deployment() {
    echo -e "\n>>> Perform a test deployment using ${TEST_IMG}...\n"
    # Validate K8s control plane
    set -x
    skopeo inspect -f "\nName: {{.Name}},\nDigest: {{.Digest}}\nCreated: {{.Created}}\n" "docker://${TEST_IMG}"
    docker pull ${TEST_IMG}
    k3d image import -c ${TEST_K8S} ${TEST_IMG}
    kubectl create namespace ${TEST_NS}
    kubectl -n ${TEST_NS} run ${TEST_ID} --image ${TEST_IMG} --restart='Never' \
                --overrides='{"apiVersion":"v1","spec":{"nodeSelector":{'\"${PZ_LAB}'/zone-A":"true"}}}' \
                -- /bin/sh -c "${TEST_CMD}"
    kubectl -n ${TEST_NS} wait --for="condition=Ready" --timeout=60s pod/${TEST_ID}
    set +x
    # Pod failure test
    echo -e "\n>>> Waiting for potential escalation...\n" && sleep 3s
    kubectl -n ${TEST_NS} get pod/${TEST_ID}
    echo
    if [[ "$(kubectl -n ${TEST_NS} get pod/${TEST_ID} -o jsonpath=\{.status.phase\})" == "${TEST_OK}" ]]; then
        echo -e "\n>>> Validation result: OK!\n"
    else
        echo -e "\n>>> Validation result: FAILED!\n"
        RET_VAL=1
    fi
}

function cleanup_test_cluster() {
    echo -e "\n>>> Cleanup...\n"
    #kubectl delete pod ${TEST_ID} -n ${TEST_NS} --grace-period=0 #--force
    k3d cluster delete ${TEST_K8S}
    docker rmi -f "${TEST_IMG}"
}

function post_install() {
    echo -e "\n>>> Installed dependencies\n"
    docker --version
    k3d version
    kubectl version --client
    helm version --template='Helm: {{.Version}} {{.GoVersion}}' && echo
    skopeo --version
}

# Parameters --------------------------------------------------------------------------------

function display_help() {
    cat <<EOF
Usage: ${0} [OPTIONS]

Options:
    -f  Freeze dependency versions.
    -c  Perform initial cleanup.
    -s  Only install minimum required binaries.
    -u  Force Update/overwrite dependencies.
    -x  Skip deployment validation.
    -n  Skip docker install.
    -h  Display help.
EOF
}

# Main --------------------------------------------------------------------------------

cat <<'EOF'

######################################################################################
##     ____ _______  __              _                          _                   ##
##    |  _ \_   _\ \/ /      ___  __| | __ _  ___      ___  ___| |_ _   _ _ __      ##
##    | |_) || |  \  /_____ / _ \/ _` |/ _` |/ _ \    / __|/ _ \ __| | | | '_ \     ##
##    |  __/ | |  /  \_____|  __/ (_| | (_| |  __/    \__ \  __/ |_| |_| | |_) |    ##
##    |_|    |_| /_/\_\     \___|\__,_|\__, |\___|    |___/\___|\__|\__,_| .__/     ##
##                                     |___/                             |_|        ##
######################################################################################

EOF

while getopts ":xfsuchn" flag; do
    case "${flag}" in
        f)
            echo "[x] Freeze dependency versions."
            PKG_FREEZE=true;;
        c)
            echo "[x] Initial cleanup configured."
            INIT_CLEANUP=true;;
        x)
            echo "[x] No setup validation is configured."
            NO_CHECK=true;;
        s)
            echo "[x] Slim install is configured."
            SLIM_SETUP=true;;
        u)
            echo "[x] Force update dependencies."
            UPDATE=true;;
        n)
            echo "[x] Skip docker install."
            NO_DOCKER=true;;
        h)
            display_help
            exit;;
        ?)
            echo "${0##*/}: invalid option -- '${OPTARG}'"
            echo "Try '${0} -h' for more information."
    esac
done

# Check for existence of ANY dependencies
if command -v "${DEPS[@]}" >/dev/null 2>&1 && [ "${UPDATE}" = false ]; then
    printf "\nSome of required dependencies are already installed, but the update flag (-u) is not set!\n\n"
    read -rp "Press ENTER to continue anyway or CTRL+C to abort..."
fi

### Basic dependencies
install_deps

### Docker
if ! command -v docker >/dev/null 2>&1 || [ "${UPDATE}" = true ]; then
    if [ ${NO_DOCKER} = false ]; then
        # Binaries
        install_docker
        if [ ${NO_CHECK} = false ] && id -nGz "${USER}" | grep -qzxF "${GRP_DOCKER}"; then
            echo -e "\n\n>>> Jump into a NEW shell for docker group privilege...\n\n" && sleep 3s
            # New shell with docker group privilege [without docker install]
            exec sg docker "$(realpath "$0") -n $*"
        fi
    fi
    # Validation
    if [ ${NO_CHECK} = false ]; then
        echo -e "\n>>> Check Docker install...\n"
        # Docker check with simple container
        docker run --rm "${CHECK_IMG}" && docker rmi -f "${CHECK_IMG}"
    fi
fi

### K3d
if ! command -v k3d >/dev/null 2>&1 || [ "${UPDATE}" = true ]; then
    # Binary
    install_k3d
    if [ ${SLIM_SETUP} = false ]; then
        # Bash completion
        setup_k3d_bash_completion
    fi
fi

### Kubectl
if ! command -v kubectl >/dev/null 2>&1 || [ "${UPDATE}" = true ]; then
    # Binary
    install_kubectl
    if [ ${SLIM_SETUP} = false ]; then
        # Bash completion
        setup_kubectl_bash_completion
    fi
fi

### Kubecolor
if ! command -v kubecolor >/dev/null 2>&1 || [ "${UPDATE}" = true ]; then
    # Binary
    install_kubecolor
fi

### Helm
if ! command -v helm >/dev/null 2>&1 || [ "${UPDATE}" = true ]; then
    # Binary
    install_helm
    if [ ${SLIM_SETUP} = false ]; then
        # Bash completion
        setup_helm_bash_completion
    fi
fi

### Skopeo
if ! command -v skopeo >/dev/null 2>&1 || [ "${UPDATE}" = true ]; then
    # Binary
    install_skopeo
    if [ ${SLIM_SETUP} = false ]; then
        # Bash completion
        setup_skopeo_bash_completion
    fi
fi

# Register cleanup
trap cleanup_test_cluster ERR INT TERM #EXIT

# Test deployment
if [ ${NO_CHECK} = false ]; then
    if [ "${INIT_CLEANUP}" = true ]; then
        cleanup_test_cluster
    fi
    # Setup cluster
    setup_test_cluster
    # Validation
    perform_test_deployment
    # Cleanup
    cleanup_test_cluster
fi

post_install

if [ ${NO_CHECK} = false ]; then
    cat <<'EOF'

##########################################################################################################
##  This shell session should be reloaded MANUALLY to make non-root user access to Docker take effect!  ##
##########################################################################################################
EOF
fi

echo -e "\nSetup is finished."
exit ${RET_VAL}
