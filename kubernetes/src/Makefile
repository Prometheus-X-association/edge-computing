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
export REGISTRY = "registry.k3d.local"
export PROJECT_ROOT = ${PWD}

COMPONENTS := builder rest-api
PTX_CORE := catalog contract consent
CONNECTOR := connector mongodb
SAMPLES := convnet gbc
EXTRA := "busybox:latest"

build:
	for mod in ${COMPONENTS}; do ${MAKE} -C "../src/$${mod}/" build; done
	${MAKE} -C ../src/ptx/ build
	${MAKE} -C ../src/samples/ build-all

rebuild: | purge build

setup:
	k3d cluster create --config=assets/k3d-dev-cluster.yaml
	kubectl create namespace ptx-edge && kubectl config set-context --current --namespace ptx-edge
	kubectl create namespace ptx-sandbox
	for img in ${COMPONENTS}; do \
		IMG=$$(docker image ls -f reference="ptx-edge/$${img}*" --format='{{.Repository}}:{{.Tag}}'); \
		# LOCAL_IMG="localhost:5000/$${IMG}"; \
		# docker tag $${IMG} $${LOCAL_IMG} && docker push $${LOCAL_IMG} && docker rmi $${LOCAL_IMG}; \
		skopeo copy --dest-tls-verify=false "docker-daemon:$${IMG}" "docker://localhost:5000/$${IMG}"; \
	done
	for img in ${PTX_CORE}; do \
		IMG=$$(docker image ls -f reference="ptx-sandbox/$${img}*" --format='{{.Repository}}:{{.Tag}}'); \
		skopeo copy --dest-tls-verify=false "docker-daemon:$${IMG}" "docker://localhost:5000/$${IMG}"; \
	done
	for img in ${CONNECTOR}; do \
		IMG=$$(docker image ls -f reference="ptx/$${img}*" --format='{{.Repository}}:{{.Tag}}'); \
		skopeo copy --dest-tls-verify=false "docker-daemon:$${IMG}" "docker://localhost:5000/$${IMG}"; \
	done
	for img in ${SAMPLES}; do \
		IMG=$$(docker image ls -f reference="samples/$${img}*" --format='{{.Repository}}:{{.Tag}}'); \
		skopeo copy --dest-tls-verify=false "docker-daemon:$${IMG}" "docker://localhost:5000/$${IMG}"; \
	done
	for img in ${EXTRA}; do \
    	# docker pull $${img}; \
		# IMG=$$(docker image ls -f reference="$${img}*" --format='{{.Repository}}:{{.Tag}}'); \
		# LOCAL_IMG="localhost:5000/$${IMG}"; \
		# docker tag $${IMG} $${LOCAL_IMG} && docker push $${LOCAL_IMG} && docker rmi $${LOCAL_IMG}; \
		skopeo copy --dest-tls-verify=false "docker://$${img}" "docker://localhost:5000/$${img}"; \
	done
	@echo
	@echo ">>> Uploaded repositories:"
	curl -Sskf -X GET http://localhost:5000/v2/_catalog | python3 -m json.tool
	@#${MAKE} -C ../src/ptx/ run-catalog
	@echo
	@echo ">>> Configured CoreDNS entries:"
	kubectl -n kube-system get configmaps coredns -o jsonpath='{.data.NodeHosts}'

status:
	@k3d cluster list --no-headers | grep -q ^ # check for existing cluster
	@kubectl get nodes --ignore-not-found -o wide
	@echo
	@kubectl -n ptx-sandbox get all --ignore-not-found -o wide || true
	@echo
	@kubectl get all,secrets,configmaps,pv,pvc,ingress --ignore-not-found -o wide || true
	@echo
	@kubectl events || true
	@echo
	@pgrep -fa "^kubectl.*port-forward.*8888:8080" || true

shell:
	-@kubectl run --rm --grace-period=3 --restart=Never --image alpine:latest -ti "shell" --command -- sh

########################################################################################################################

run-catalog:
	kubectl -n ptx-sandbox apply -f assets/ptx-sandbox-setup.yaml -l app=catalog
	kubectl -n ptx-sandbox wait --for="condition=Ready" --timeout=20s pod/catalog
	@echo
	@kubectl -n ptx-sandbox get all -o wide
	@echo
	@echo ">>> Catalog is exposed as 'catalog.ptx-sandbox.svc.cluster.local'"
	kubectl run --rm --restart=Never --image busybox:latest -ti "check" --command -- \
								sh -c "nslookup catalog.ptx-sandbox.svc.cluster.local; \
								wget -qO- http://catalog.ptx-sandbox.svc.cluster.local:3002/__admin/health" || true

run-pdc: run-catalog
	kubectl apply -f assets/ptx-pdc-setup.yaml
	kubectl wait --for="condition=Ready" --timeout=20s pod/pdc
	@echo "Waiting for PDC to set up..."
	( kubectl logs -f pod/pdc -c ptx-connector & ) | timeout 60 grep -m1 "Server running on"
	@echo
	@kubectl get all -o wide
	@echo
	@echo ">>> PDC is exposed as 'pdc.ptx-edge.svc.cluster.local'"
	kubectl run --rm --restart=Never --image busybox:latest -ti "check" --command -- \
								sh -c "nslookup pdc.ptx-edge.svc.cluster.local; \
								 	   wget -qS pdc.ptx-edge.svc.cluster.local:3000/ >/dev/null" || true
	@echo
	$(eval NODE_IP = `kubectl get pod -l app=pdc -o jsonpath='{.items[].status.hostIP}'`)
	@echo ">>> PDC is exposed on http://${NODE_IP}:30030/"
	@curl -Ssf "http://${NODE_IP}:30030/" | grep "href"

run-api:
	kubectl apply -f assets/ptx-rest-api-setup.yaml
	kubectl wait --for="condition=Ready" --timeout=20s pod/rest-api
	( kubectl port-forward service/rest-api 8888:8080 & ) && sleep 3
	@echo
	@echo ">>> REST-API is exposed on http://localhost:8888/ptx-edge/v1/ui/"
	@curl -I "http://localhost:8888/ptx-edge/v1/ui/"
	curl -LSs "http://localhost:8888/ptx-edge/v1/versions" | python3 -m json.tool

run-builder:
	kubectl apply -f assets/ptx-builder-pod.yaml
	kubectl wait --for="condition=Ready" --timeout=20s pod/builder
	@echo
	kubectl get all -o wide
	@echo
	-kubectl exec -ti pod/builder -- sh
	kubectl delete pods,secrets -l app=builder --now --wait

########################################################################################################################

run-sample-convnet:
	kubectl apply -f assets/ptx-samples-convnet-job.yaml
	kubectl wait --for='jsonpath={.status.phase}=Bound' --timeout=10s pvc/worker-pvc
	@echo
	kubectl get all,pv,pvc -o wide
	@echo
	@#kubectl logs -f --all-containers --prefix --ignore-errors -l app=consumer
	kubectl wait --for="condition=PodReadyToStartContainers" pods -l app=consumer
	kubectl logs -f --prefix job/consumer builder
	kubectl wait --for="condition=ContainersReady" pods -l app=consumer
	kubectl logs -f --prefix job/consumer worker

run-sample-gbc:
	kubectl apply -f assets/ptx-samples-gbc-job.yaml
	kubectl wait --for='jsonpath={.status.phase}=Bound' --timeout=10s pvc/worker-pvc
	@echo
	kubectl get all,pv,pvc -o wide
	@echo
	@#kubectl logs -f --all-containers --prefix --ignore-errors -l app=consumer
	kubectl wait --for="condition=PodReadyToStartContainers" pods -l app=consumer
	kubectl logs -f --prefix job/consumer builder
	kubectl wait --for="condition=ContainersReady" pods -l app=consumer
	@#kubectl logs -f --prefix -l app=consumer
	kubectl logs -f --prefix job/consumer worker

########################################################################################################################

run-test-job:
	kubectl apply -f assets/ptx-test-worker-job.yaml
	kubectl wait --for='jsonpath={.status.phase}=Bound' --timeout=20s pvc/worker-pvc
	@echo
	kubectl get all,pv,pvc -o wide
	@echo
	@# kubectl wait --for="condition=Complete" --timeout=20s job/consumer
	@# kubectl logs job/consumer builder && kubectl logs job/consumer worker
	kubectl wait --for="condition=PodReadyToStartContainers" --timeout=10s pods -l app=consumer
	kubectl logs -f --prefix job/consumer-test-job builder
	kubectl wait --for="condition=ContainersReady" --timeout=10s pods -l app=consumer
	kubectl logs -f --prefix job/consumer-test-job worker


run-test-img:
	kubectl apply -f assets/ptx-test-worker-img.yaml
	kubectl wait --for='jsonpath={.status.phase}=Bound' --timeout=20s pvc/worker-pvc
	@echo
	kubectl get all,pv,pvc -o wide
	@echo
	@# kubectl wait --for="condition=Complete" --timeout=20s job/consumer
	@# kubectl logs job/consumer builder && kubectl logs job/consumer worker
	kubectl wait --for="condition=PodReadyToStartContainers" --timeout=10s pods -l app=consumer
	kubectl logs -f --prefix job/consumer-test-img builder
	kubectl wait --for="condition=ContainersReady" pods --timeout=10s -l app=consumer
	kubectl logs -f --prefix job/consumer-test-img worker

########################################################################################################################

launch: | rebuild setup run-pdc run-builder

log-pdc:
	kubectl logs --prefix --ignore-errors -f pdc ptx-connector || true

log-catalog:
	kubectl -n ptx-sandbox logs --prefix --ignore-errors -f pods/catalog catalog-wiremock || true

########################################################################################################################

stop:
	( pgrep -f "^kubectl.*port-forward.*8888:8080" ) | xargs -r kill
	kubectl delete namespace ptx-edge --ignore-not-found --now && kubectl create namespace ptx-edge
	kubectl delete namespace ptx-sandbox --ignore-not-found --now && kubectl create namespace ptx-sandbox
	skopeo delete --tls-verify=false "docker://localhost:5000/myworker:latest" || true
	kubectl delete events --all

clear:
	-docker ps -aq -f name=ptx-catalog | xargs -r docker rm -f
	k3d cluster delete dev || true

purge: clear
	rm -rf ${PROJECT_ROOT}/.cache
	docker image ls -qf "reference=ptx/*" -f "reference=ptx-edge/*" \
					 -f "reference=ptx-sandbox/*" -f "reference=samples/*" | xargs -r docker rmi -f
	docker image prune -f

.PHONY:
.DEFAULT_GOAL := setup