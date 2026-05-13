# Dataset Testing API

# Usage

## Simple HTTP server (unprotected, unauthenticated)

Serving dataset files directly from `./resource` directory unprotected, unauthorized.

Dependencies:
- only standard Python3

```bash
# API listens on 0.0.0.0:8888
$ ./run_http_api.sh
# E.g., `curl -O http://localhost:8888/static/dp1/train_data.npz` 
```

## FastAPI-based multipurpose API server (protected, authorized)

Use TLS with self-signed certificate and common name `datasource.ptx.localhost` for secure connections.

Serving datasets directly from `./resource` directory under `/static/` path prefix.

Serving datasets with basic authentication under `/dataset/` prefix using the path structure
`/<privacy_zone>/<data_file>`.

```bash
# API listens on 0.0.0.0:8443
$ ./run_docker_api.sh
# E.g., `curl -k -O https://datasource.ptx.localhost:8443/static/dp2/train_data.npz`
# E.g., `curl -k -u <user>:<pass> -O https://datasource.ptx.localhost:8443/dataset/dp1/train_data.npz`

```