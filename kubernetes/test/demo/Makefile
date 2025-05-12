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

start:
	@bash start-topo.sh


viewer:
	@( kubectl proxy 2>/dev/null & ) || exit 0
	@docker run --rm -d -q --net=host -v ~/.kube:/kube --name kube-ops-viewer -it hjacobs/kube-ops-view \
        --port=8081 --query-interval=3 --kubeconfig-path=/kube/config >/dev/null
	@echo
	@echo "Viewer is available on http://127.0.0.1:8081/"
	@echo

setup:
	echo

stop:
	@docker kill kube-ops-viewer >/dev/null 2>&1 || exit 0
	@bash stop-topo.sh