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

depends:
	cd ./scripts && ./install_deps.sh -u

########################################################################################################################

0-build:
	bash scripts/0-build-images.sh

1-init:
	bash scripts/1-start-topo.sh

2-viewer:
	( kubectl proxy 2>/dev/null & ) || exit 0
	docker run --rm -d -q --net=host -v ~/.kube:/kube --name kube-ops-viewer -it hjacobs/kube-ops-view \
        		--port=8081 --query-interval=3 --kubeconfig-path=/kube/config >/dev/null
	( docker logs -f kube-ops-viewer & ) | timeout 30 grep -m1 "Listening on" >/dev/null
	echo
	echo "K8s Ops Viewer is available on http://localhost:8081/"
	echo

3-edge:
	bash scripts/3-setup-ptx-edge.sh

4-demo:
	bash scripts/4-run-demo.sh

setup: | 0-build 1-init 2-viewer 3-edge 4-demo

########################################################################################################################

stop-demo:
	#-for uc in rsc/task*.yaml; do kubectl delete -f $${uc} --now --wait --ignore-not-found; done
	bash scripts/stop-demo.sh

delete-edge:
	bash scripts/delete-ptx-edge.sh

shutdown-cluster:
	bash scripts/shutdown-topo.sh
	docker kill kube-ops-viewer >/dev/null 2>&1 || exit 0

teardown: | stop-demo delete-edge shutdown-cluster

########################################################################################################################

status:
	@k3d cluster list --no-headers | grep -q ^ # check for existing cluster
	bash ./scripts/status.sh

shell:
	-@kubectl run --rm --grace-period=3 --restart=Never --image alpine:latest -ti "shell" --command -- sh

top:
	watch -d -n1 kubectl top pod -l tier=worker --sum --containers

log:
	kubecolor logs --prefix -l tier=worker --follow

cleanup:
	docker image ls -qf "reference=ptx/*" -f "reference=ptx-edge/*" \
					 -f "reference=ptx-sandbox/*" -f "reference=ghcr.io/alelevente/*" | xargs -r docker rmi -f
	docker image prune -f

########################################################################################################################

SHELL := bash
.SILENT:	# Set silent mode (-s) by default
.PHONY:		# Set all target phony
.DEFAULT_GOAL := setup