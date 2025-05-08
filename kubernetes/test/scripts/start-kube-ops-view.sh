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
INTERVAL=3
KUBE_PROXY_PID=""
SCRIPT_DIR=$(readlink -f "$(dirname "$0")")
source "${SCRIPT_DIR}/helper.sh"

LOG "Kube-ops-view is available on http://127.0.0.1:8081/"
echo

function cleanup() {
    set +x
    #pkill -f "kubectl proxy"
    [ -d "/proc/${KUBE_PROXY_PID}" ] && kill ${KUBE_PROXY_PID}
}
trap cleanup ERR INT

set -x
kubectl proxy &
KUBE_PROXY_PID=$!
docker run --rm --net=host -v ~/.kube:/kube -it hjacobs/kube-ops-view \
        --port ${PORT} --query-interval ${INTERVAL} --kubeconfig-path=/kube/config
cleanup
