# PTX-Edge Extension Testing

## Overview

The testing of the PTX-Edge extension on the Kubernetes ecosystem is
performed using the [Kind](https://kind.sigs.k8s.io/) tool.

## Preparations and setup

The test environment can be set up locally based on Ubuntu 22.04 LTS by
cloning the repository and executing the following script.
```bash
$ git clone https://github.com/Prometheus-X-association/edge-computing.git
$ cd kubernetes/test
$ ./setup_test_env.sh
```
The script installs the required dependencies
- [Docker](https://get.docker.com/) (latest)
- [Kind](https://github.com/kubernetes-sigs/kind/releases/tag/v0.24.0) (v0.24.0)
- [Kubectl](https://github.com/kubernetes/kubectl/releases/tag/v0.31.0) (v1.31.0)

and performs a simple test deployment on a temporary Kubernetes
cluster for validation.

The setup script also supports a rootless installation by using
the `-r` flag.
```bash
./setup_test_env.sh -r
```
See more about rootless mode and its limitations in
[here](https://docs.docker.com/engine/security/rootless/)
and [here](https://kind.sigs.k8s.io/docs/user/rootless/).

## Extension Installation

TBD

## Unit tests

TBD

## REST-API Mockup

The repository also provides a mockup REST-API under `mock-api` folder
for testing purposes based on its 
[OpenAPI3.0 specification](mock-api/swagger_server/swagger/swagger.yaml).

See further the related [REAMDE.md](mock-api/README.md).
