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

1-init:
	bash 1-start-topo.sh

2-viewer:
	( kubectl proxy 2>/dev/null & ) || exit 0
	docker run --rm -d -q --net=host -v ~/.kube:/kube --name kube-ops-viewer -it hjacobs/kube-ops-view \
        		--port=8081 --query-interval=3 --kubeconfig-path=/kube/config >/dev/null
	( docker logs -f kube-ops-viewer & ) | timeout 30 grep -m1 "Listening on" >/dev/null
	echo
	echo "K8s Ops Viewer is available on http://127.0.0.1:8081/"
	echo

3-setup:
	bash 3-setup-ptx-edge.sh

4-demo:
	bash 4-run-demo.sh

5-delete:
	bash 5-delete-ptx-edge.sh

6-shutdown:
	docker kill kube-ops-viewer >/dev/null 2>&1 || exit 0
	bash 6-stop-topo.sh

status:
	@k3d cluster list --no-headers | grep -q ^ # check for existing cluster
	bash 0-status.sh

clear:
	#-for uc in rsc/task*.yaml; do kubectl delete -f $${uc} --now --wait --ignore-not-found; done
	-kubectl delete jobs,pv,pvc,events --all --now --wait=false --ignore-not-found

all: | 1-init 2-viewer 3-setup 4-demo 5-delete 6-shutdown

.SILENT:	# Set silent mode (-s) by default
.PHONY := 1-init 2-viewer 3-setup 4-demo 5-delete 6-shutdown status clear all
.DEFAULT_GOAL := all