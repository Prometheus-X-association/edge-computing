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
export PROJECT_ROOT=${PWD}
export REGISTRY=registry.k3d.local
export REGISTRY_PORT=5000
export REGISTRY_USER=admin
export REGISTRY_SECRET=admin

K3D_REG := registry.k3d.localhost:5000
CREDS := ${REGISTRY_USER}:${REGISTRY_SECRET}
CA_DIR := ${PROJECT_ROOT}/registry/.certs/ca

COMPONENTS := builder rest-api scheduler registry
PTX_CORE := catalog contract consent
CONNECTOR := connector mongodb
SAMPLES := convnet gbc
EXTRA := "busybox:latest"

build:
	for mod in ${COMPONENTS}; do ${MAKE} -C $${mod} build; done
	${MAKE} -C ptx build
	${MAKE} -C samples build-all

rebuild: | purge build

setup:
	k3d cluster create --config=assets/k3d-dev-cluster.yaml
	kubectl create namespace ptx-edge && kubectl config set-context --current --namespace ptx-edge
	kubectl create namespace ptx-sandbox
	for img in ${COMPONENTS}; do \
		IMG=$$(docker image ls -f reference="ptx-edge/$${img}*" --format='{{.Repository}}:{{.Tag}}'); \
		# LOCAL_IMG="localhost:5000/$${IMG}"; \
		# docker tag $${IMG} $${LOCAL_IMG} && docker push $${LOCAL_IMG} && docker rmi $${LOCAL_IMG}; \
		skopeo copy --dest-cert-dir=${CA_DIR} --dest-creds=${CREDS} docker-daemon:$${IMG} docker://${K3D_REG}/$${IMG}; \
	done
	for img in ${PTX_CORE}; do \
		IMG=$$(docker image ls -f reference="ptx-sandbox/$${img}*" --format='{{.Repository}}:{{.Tag}}'); \
		skopeo copy --dest-cert-dir=${CA_DIR} --dest-creds=${CREDS} docker-daemon:$${IMG} docker://${K3D_REG}/$${IMG}; \
	done
	for img in ${CONNECTOR}; do \
		IMG=$$(docker image ls -f reference="ptx/$${img}*" --format='{{.Repository}}:{{.Tag}}'); \
		skopeo copy --dest-cert-dir=${CA_DIR} --dest-creds=${CREDS} docker-daemon:$${IMG} docker://${K3D_REG}/$${IMG}; \
	done
	for img in ${SAMPLES}; do \
		IMG=$$(docker image ls -f reference="samples/$${img}*" --format='{{.Repository}}:{{.Tag}}'); \
		skopeo copy --dest-cert-dir=${CA_DIR} --dest-creds=${CREDS} docker-daemon:$${IMG} docker://${K3D_REG}/$${IMG}; \
	done
	for img in ${EXTRA}; do \
    	# docker pull $${img}; \
		# IMG=$$(docker image ls -f reference="$${img}*" --format='{{.Repository}}:{{.Tag}}'); \
		# LOCAL_IMG="localhost:5000/$${IMG}"; \
		# docker tag $${IMG} $${LOCAL_IMG} && docker push $${LOCAL_IMG} && docker rmi $${LOCAL_IMG}; \
		skopeo copy --dest-cert-dir=${CA_DIR} --dest-creds=${CREDS} "docker://$${img}" "docker://${K3D_REG}/$${img}"; \
	done
	@echo
	kubectl create configmap registry-root-ca.crt --from-file=ca.crt=registry/.certs/ca/ca.crt
	@echo
	@echo ">>> Uploaded images:"
	curl -Sskf --cacert ${CA_DIR}/ca.crt -u ${CREDS} -X GET https://${K3D_REG}/v2/_catalog | python3 -m json.tool
	@#${MAKE} -C ../src/ptx/ run-catalog
	@echo
	@echo ">>> Configured CoreDNS entries:"
	kubectl -n kube-system get configmaps coredns -o jsonpath='{.data.NodeHosts}'

status:
	@k3d cluster list --no-headers | grep -q ^ # check for existing cluster
	@kubectl get nodes --ignore-not-found -o wide
	@echo
	@-kubectl -n ptx-sandbox get all --ignore-not-found -o wide
	@echo
	@-kubectl get all,endpointslices,secrets,configmaps,pv,pvc,ingress,ingressroutes.traefik.io,middlewares.traefik.io \
 			--ignore-not-found -o wide
	@echo
	@-kubectl events
	@echo
	@pgrep -fa "^kubectl.*port-forward.*8888:8080" || true

shell:
	-@kubectl run --rm --grace-period=3 --restart=Never --image alpine:latest -ti "shell" --command -- sh

########################################################################################################################

run-catalog:
	kubectl -n ptx-sandbox apply -f assets/ptx-sandbox-setup.yaml -l app=catalog
	kubectl -n ptx-sandbox wait --for="condition=Ready" --timeout=30s pod/catalog
	@echo
	@kubectl -n ptx-sandbox get all -o wide
	@echo
	@echo ">>> Catalog is exposed as 'catalog.ptx-sandbox.svc.cluster.local'"
	-kubectl run --rm --restart=Never --image busybox:latest -ti "check" --command -- \
								sh -c "nslookup catalog.ptx-sandbox.svc.cluster.local; \
								wget -T3 -qO- http://catalog.ptx-sandbox.svc.cluster.local:3002/__admin/health"

run-pdc-pod: run-catalog
	kubectl apply -f assets/ptx-pdc-pod.yaml
	kubectl wait --for="condition=Ready" --timeout=30s pod/pdc
	@echo "Waiting for PDC to set up..."
	( kubectl logs -f pod/pdc -c ptx-connector & ) | timeout 60 grep -m1 "Server running on"
	@echo
	@kubectl get all -o wide
	@echo
	@echo ">>> PDC is exposed as 'pdc.ptx-edge.svc.cluster.local'"
	-kubectl run --rm --restart=Never --image busybox:latest -ti "check" --command -- \
								sh -c "nslookup pdc.ptx-edge.svc.cluster.local; \
								 	   wget -T3 -qS http://pdc.ptx-edge.svc.cluster.local:3000/ >/dev/null"
	@echo
	$(eval NODE_IP = `kubectl get pod -l app=pdc -o jsonpath='{.items[].status.hostIP}'`)
	@echo ">>> PDC is exposed on http://${NODE_IP}:30003/"
	@curl -Ssf "http://${NODE_IP}:30003/" | grep "href"

run-pdc-daemon-headless: run-catalog
	kubectl apply -f assets/ptx-pdc-daemon_headless.yaml
	kubectl wait --for=jsonpath='.status.numberReady'=1 --timeout=30s daemonset/pdc
	@echo "Waiting for PDC to set up..."
	for pod in $$(kubectl get pods -l app=pdc -o jsonpath='{.items[*].metadata.name}'); do \
		( kubectl logs -f pods/$${pod} -c ptx-connector & ) | timeout 90 grep -m1 "Server running on"; \
	done
	@echo
	@kubectl get all -o wide
	@echo
	@echo ">>> PDC is exposed as 'pdc.ptx-edge.svc.cluster.local'"
	-kubectl run --rm --restart=Never --image busybox:latest -ti "check" --command -- \
								sh -c "nslookup pdc-zone-a.ptx-edge.svc.cluster.local; \
									   nslookup pdc-zone-b.ptx-edge.svc.cluster.local; \
								 	   wget -T3 -qS http://pdc-zone-a.ptx-edge.svc.cluster.local:30003/ >/dev/null"
	@echo
	$(eval NODE_IP = `kubectl get pod -l app=pdc -o jsonpath='{.items[].status.hostIP}'`)
	@echo ">>> PDC is exposed on http://${NODE_IP}:30003/"
	@curl -Ssf "http://${NODE_IP}:30003/" | grep "href"
	@#kubectl exec -ti ds/pdc --container builder -- sh

run-pdc-daemon-cluster: run-catalog
	kubectl apply -f assets/ptx-pdc-daemon_cluster.yaml
	kubectl apply -f assets/ptx-pdc-ingess.yaml
	kubectl wait --for=jsonpath='.status.numberReady'=1 --timeout=30s daemonset/pdc
	@echo "Waiting for PDC to set up..."
	for pod in $$(kubectl get pods -l app=pdc -o jsonpath='{.items[*].metadata.name}'); do \
		( kubectl logs -f pods/$${pod} -c ptx-connector & ) | timeout 90 grep -m1 "Server running on"; \
	done
	@echo
	@kubectl get all -o wide
	@echo
	@echo ">>> PDC is exposed as 'pdc.ptx-edge.svc.cluster.local'"
	-kubectl run --rm --restart=Never --image busybox:latest -ti "check" --command -- \
								sh -c "nslookup pdc-zone-a.ptx-edge.svc.cluster.local; \
									   nslookup pdc-zone-b.ptx-edge.svc.cluster.local; \
								 	   wget -T3 -qS http://pdc-zone-a.ptx-edge.svc.cluster.local:3000/ >/dev/null"
	wget -T3 -O /dev/null -qS http://localhost:8888/ptx-edge/zone-a/pdc/
	wget -T3 -O /dev/null -qS http://localhost:8888/ptx-edge/zone-b/pdc/
	@#kubectl exec -ti ds/pdc --container builder -- sh

run-api:
	kubectl apply -f assets/ptx-rest-api-pod.yaml
	kubectl wait --for="condition=Ready" --timeout=30s pod/rest-api
	@#( kubectl port-forward service/rest-api 8888:8080 & ) && sleep 3
	@echo
	@echo ">>> REST-API is exposed on http://localhost:8888/ptx-edge/api/v1/ui/"
	@sleep 3
	wget -T3 -qS http://localhost:8888/ptx-edge/api/v1/ui/ >/dev/null
	curl -LSs "http://localhost:8888/ptx-edge/api/v1/versions" | python3 -m json.tool

run-builder:
	envsubst <assets/ptx-builder-pod.yaml '$${DH_TOKEN}' | kubectl apply -f=-
	kubectl wait --for="condition=Ready" --timeout=30s pod/builder
	@echo
	kubectl get all -o wide
	@echo
	-kubectl exec -ti pod/builder -- sh
	kubectl delete pods/builder --now --wait
	kubectl delete pods,secrets -l app=builder -l app=worker --now --wait

run-scheduler:
	kubectl apply -f assets/ptx-scheduler-pod.yaml
	kubectl wait --for="condition=Ready" --timeout=30s pod/scheduler
	@echo
	kubectl get all -o wide
	@echo
	-kubectl exec -ti pod/scheduler -- sh || true
	kubectl delete pods/scheduler --now --wait
	kubectl delete pods -l app=worker

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
	kubectl wait --for='jsonpath={.status.phase}=Bound' --timeout=30s pvc/worker-pvc
	@echo
	kubectl get all,pv,pvc -o wide
	@echo
	@# kubectl wait --for="condition=Complete" --timeout=30s job/consumer
	@# kubectl logs job/consumer builder && kubectl logs job/consumer worker
	kubectl wait --for="condition=PodReadyToStartContainers" --timeout=10s pods -l app=consumer
	kubectl logs -f --prefix job/consumer-test-job builder
	kubectl wait --for="condition=ContainersReady" --timeout=10s pods -l app=consumer
	kubectl logs -f --prefix job/consumer-test-job worker


registry-ca:
	kubectl create configmap registry-root-ca.crt --from-file=ca.crt=registry/.certs/ca/ca.crt || true

run-test-img: registry-ca
	kubectl apply -f assets/ptx-test-worker-img.yaml
	kubectl wait --for='jsonpath={.status.phase}=Bound' --timeout=30s pvc/worker-pvc
	@echo
	kubectl get all,pv,pvc,configmaps,secrets -o wide
	@echo
	@# kubectl wait --for="condition=Complete" --timeout=30s job/consumer
	@# kubectl logs job/consumer builder && kubectl logs job/consumer worker
	kubectl wait --for="condition=PodReadyToStartContainers" --timeout=10s pods -l app=consumer
	kubectl logs -f --prefix job/consumer-test-img builder
	kubectl wait --for="condition=ContainersReady" pods --timeout=10s -l app=consumer
	kubectl logs -f --prefix job/consumer-test-img worker

ifneq (,$(wildcard ./.creds/dockerhub.token))
    include ./.creds/dockerhub.token
    export
endif

run-test-secret:
	envsubst <assets/ptx-test-worker-secret.yaml '$${DH_TOKEN}' | kubectl apply -f=-
	kubectl wait --for='jsonpath={.status.phase}=Bound' --timeout=30s pvc/worker-pvc
	@echo
	kubectl get all,pv,pvc,configmaps,secrets -o wide
	@echo
	@# kubectl wait --for="condition=Complete" --timeout=30s job/consumer
	@# kubectl logs job/consumer builder && kubectl logs job/consumer worker
	kubectl wait --for="condition=PodReadyToStartContainers" --timeout=10s pods -l app=consumer
	kubectl logs -f --prefix job/consumer-test-secret builder
	kubectl wait --for="condition=ContainersReady" pods --timeout=10s -l app=consumer
	kubectl logs -f --prefix job/consumer-test-secret worker

########################################################################################################################

launch: | rebuild setup run-pdc run-builder

log-pdc:
	-kubectl logs --prefix --ignore-errors -f pdc ptx-connector

log-catalog:
	-kubectl -n ptx-sandbox logs --prefix --ignore-errors -f pods/catalog catalog-wiremock

########################################################################################################################

stop:
	( pgrep -f "^kubectl.*port-forward.*8888:8080" ) | xargs -r kill
	kubectl delete namespace ptx-edge --ignore-not-found --now && kubectl create namespace ptx-edge
	kubectl delete namespace ptx-sandbox --ignore-not-found --now && kubectl create namespace ptx-sandbox
	skopeo delete --cert-dir=${CA_DIR} --creds=${CREDS} docker://${K3D_REG}/myworker:latest || true
	kubectl delete events --all

clear:
	-docker ps -aq -f name=ptx-catalog | xargs -r docker rm -f
	-k3d cluster delete dev

purge: clear
	rm -rf ${PROJECT_ROOT}/.cache
	docker image ls -qf "reference=ptx/*" -f "reference=ptx-edge/*" \
					 -f "reference=ptx-sandbox/*" -f "reference=samples/*" | xargs -r docker rmi -f
	docker image prune -f

.PHONY:
.DEFAULT_GOAL := setup