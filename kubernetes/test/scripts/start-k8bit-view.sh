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
PORT=8081
K8BIT_REPO=git@github.com:learnk8s/k8bit.git
KUBE_PROXY_PID=""
SCRIPT_DIR=$(readlink -f "$(dirname "$0")")
source "${SCRIPT_DIR}/helper.sh"

function cleanup() {
    set +x
    rm -rf "${TMP_DIR}" || exit
}

trap cleanup ERR INT

#set -x
TMP_DIR=$(mktemp -d) && pushd "${TMP_DIR}" || exit 1
git clone ${K8BIT_REPO} && cd k8bit
LOG "K8bit view in available on http://127.0.0.1:8081/k8bit/"
echo
kubectl proxy --address=0.0.0.0 --port=${PORT} --www=. --www-prefix=/k8bit/
cleanup
