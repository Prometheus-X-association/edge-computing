install: mock-api/Dockerfile
	# bash setup_kind_test_env.sh -xs
	docker build -t ptx-edge-api:0.1 mock-api/

run: install
	# bash create_test_cluster.sh
	docker run --rm --name ptx-edge-api -p 8080:8080 -it ptx-edge-api:0.1

cleanup:
	# kind delete cluster -n "test"
	docker rmi ptx-edge-api:0.1

.PHONY: install run cleanup
.DEFAULT_GOAL := run