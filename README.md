# Edge computing — AI processing BB

The *Edge Computing (Decentralized AI processing) BB* (BB-02) provides value-added services
exploiting an underlying distributed edge-computing infrastructure (e.g., owned and operated
by Cloud Providers).

These services target two main high-level goals:

- **Privacy-preserving**, where data is kept close(r) to the user, more exactly within a
  pre-defined domain, called a _privacy zone_, that is eligible to process the private data.
- **Efficient near-data processing**, with optimized computation performance, resource
  utilization, and data privacy.

In general, the main goal is to move (AI-related) data processing capabilities close to the
data source and execute them on-site. If the execution capability is available on-site, that
is, in the virtual/physical node storing the data, the data-consuming software function (as a
FaaS-based operation) or container (as a CaaS based operation) is launched there (e.g., by a
Kubernetes-based orchestration framework). Thus, we can avoid the transmission of a large
number of data and address privacy challenges designated by geographical or provider-related
rules, regulations, or demands.

As a more realistic scenario, the data and the function can also be moved for processing but
only within a pre-defined **privacy zone**. This privacy zone primarily encompasses a set of
worker nodes (using the Kubernetes terminology), that are suitable in the sense of pre-defined
privacy rules and where processing functions can and should be deployed on demand.

From the viewpoint of data processing capabilities, a processing function (deployed within an
eligible privacy zone) can perform simple data preprocessing, filtering, or manipulation
actions on the private data, or more complex tasks, such as federated AI model learning steps.
This is uniformly enabled by advanced containerization technologies, such as _docker_, where
the data processing piece of code is bundled with its dependencies and software resources in a
standalone deployable package, in a lightweight and portable way.Nevertheless
This container-based approach also opens new possibilities to support the execution of
standalone and portable components of other building blocks provided these block parts can be
seamlessly operated in a cloud-native or serverless execution environments.

## Table of Contents

<!-- TOC -->

* [Edge computing — AI processing BB](#edge-computing--ai-processing-bb)
    * [Table of Contents](#table-of-contents)
    * [Design Document](#design-document)
    * [Building Instructions](#building-instructions)
        * [Kubernetes Setup](#kubernetes-setup)
        * [Installation](#installation)
            * [Default Setup](#default-setup)
            * [Dedicated Deployment Configurations](#dedicated-deployment-configurations)
            * [Example Demo Setups](#example-demo-setups)
        * [Development & Testing](#development--testing)
    * [Running Instructions](#running-instructions)
    * [Example Usage](#example-usage)
        * [REST-API](#rest-api)
        * [Testing](#testing)
        * [Examples](#examples)
    * [Test Definitions](#test-definitions)
    * [Unit Testing](#unit-testing)
        * [Setup Test Environment](#setup-test-environment)
        * [Run Tests](#run-tests)
        * [Expected Results](#expected-results)
    * [Component-Level Testing](#component-level-testing)
        * [Setup Test Environment](#setup-test-environment-1)
        * [Run Tests](#run-tests-1)
        * [Expected Results](#expected-results-1)

<!-- TOC -->

## Design Document

> [!IMPORTANT]
>
> See the comprehensive design document of the Edge Computing building block [here](docs/design-document.md).

> [!IMPORTANT]
>
> See the developer/technical document of the building block components [here](kubernetes/design/README.md).

Since the functionalities of the Edge Computing BB fundamentally rely on the **Kubernetes** (K8s)
container orchestration platform (realistically spanning multiple providers' domains/clouds),
its value-added services are implemented as standalone software containers, operated in a
dedicated Kubernetes namespace, and several PTX-tailored extensions of the Kubernetes
framework itself.

The elements of BB-02's main functionalities cover the following:

- Provide a _generic runtime environment_ for data processing functions.
- Provide the ability to deploy _pre-built containers with privacy-preserving_ options.
- Provide the capability of orchestrating data processing by _privacy-zone_ metadata.
- Use the _PTX Connector_ to interact with PTX core elements.
- Implement and control the process of getting data for _data consumer functions/software_.
- Implement a separate _REST-API interface_ for the integration with PTX dataspace.
- Implement a dedicated scheduler for managing compute resources efficiently and in a
  privacy-preserving manner.

See the main technical document in [kubernetes/design](kubernetes/design), which describes
in detail how the building block components are realized and bound to the Kubernetes'
architecture features.

![Schematic architecture of BB02](kubernetes/design/Kubernetes_ref_architecture.png)

*Schematic design architecture of binding BB-02's functional components to K8s internal
objects.*

## Building Instructions

### Kubernetes Setup

Since BB-02 primarily consists of extension modules to the widespread Kubernetes framework,
instead of a (set of) standalone software, its installation and setup require different
steps, and most of all, an operating **vanilla Kubernetes cluster** as a prerequisite.

The fundamental Kubernetes features, on which the designed extension modules rely, are
specifically chosen to support a wide variety of Kubernetes versions (e.g., preferring
Ingress routes instead of the newer API Gateway entries).

Nevertheless, currently Kubernetes version **1.31.5** and above are preferred and tested.

There are many methods and tools for setting up a production-grade Kubernetes cluster on
a local machine. For example,

- consult with the Kubernetes'
  [official documentation](https://kubernetes.io/docs/setup/),
- pick any of the numerous
  [certified platform solutions](https://kubernetes.io/docs/setup/production-environment/turnkey-solutions/), or
- choose one of the managed Kubernetes services available online at
  top-tier [cloud provider](https://kubernetes.io/docs/setup/production-environment/turnkey-solutions/)
  or in the [EU](https://european-alternatives.eu/category/managed-kubernetes-services).

### Installation

Since the BB-02 building block is not a standalone data processing service per se, but an
over-the-top platform for executing or operating other data processing functionalities
in a native cloud environment.
Thus, BB-02's installation steps highly rely on the actual setup of the underlying
Kubernetes orchestration framework.
Nevertheless, except minor platform-specific configurations, e.g., routing with K8s
deployment's application gateway or using built-in certificate management services,
the installation process can be considered system-independent assuming the configuration
profile and context to the underlying Kubernetes cluster is available and set by default.

The installation and configuration steps are grouped together into separate helper scripts
with a dedicated [Makefile](Makefile), that are intended to

- download and install required software and system dependencies,
- assemble a specific version of the PTX Connector component (PDC) tailored for K8s,
- compile dedicated containers of building block components,
- install and configure the building block over the default kKubernetes cluster
  using either command line tools and/or the Kubernetes' package manager,
  called [Helm](https://helm.sh/) internally.

#### Default Setup

The easiest and straightforward way to set up BB-02's **ptx-edge K8s extension**,
(assuming a valid default `kubectl` profile for a running Kubernetes cluster),
use the following command issued in the project's root folder:

```bash
$ make setup
```

> [!NOTE]
>
> Since BB-02's additional features are still under development, Makefile targets currently
> (_setup_ / _run_ / _cleanup_) point directly to the targets of the latest tested readiness
> level's Makefile in `kubernetes/test/levels`, that assumes a default locally emulated
> Kubernetes cluster!

> [!TIP]
>
> The configured level based on the `ptx-edge`-internal
> [definitions](kubernetes/test/README.md#overview) is **Level 5**.

Current development of BB-02 addresses additional features to ease the development and usage 
of the building block feature for human users in order to fulfill the goals of final Level 6. 

#### Dedicated Deployment Configurations

Furthermore, there are dedicated deployment scenarios for BB02's intended application scenarios
in [kubernetes/deployment](kubernetes/deployment), e.g., the latest deployment configuration
of building block BB-02 operated at the BME side.

These deployment configurations are not designed for general applicability, but for specific
cloud environments and use case scenarios. These deployment setups encompass comprehensive
configuration options for a given use case scenario, including

- domain/server information,
- certificate management,
- additional security hardening,
- Kubernetes-related extra metadata,
- and more.

Nevertheless, these can be used as a starting point by advanced users to create similar
deployment configurations for other use cases.

Usually, these configurations require only minor modifications, e.g., changing public domain
DNS, load balancer IP, etc., to adjust them to deployment scenarios of the same kind.
For the available configuration options, consult with the
`config.sh` files and `templates` folders.

#### Example Demo Setups

There are several deployment setups in [kubernetes/test/demos](kubernetes/test/demos) for
demonstrating `ptx-edge` capabilities over a local emulated Kubernetes cluster.
Although, these configuration setups are designed for executing test workflows, it contains
useful examples how the building block component can be precompiled, defined, set up,
and configured to use them in different scenarios.

For the configuration and deployment options, consult with the related `Makefile`,
`install.sh`, `"*-topo.sh`, and `setup-*.sh` helper scripts, as well as the K8s manifest
template files under the local `./rsc` folders.

### Development & Testing

> [!NOTE]
>
> The BB-02 module is unique in that sense that it cannot be seamlessly run by a
> container framework, such as Docker or Podman, as it is inherently based on container
> orchestration features of a higher architecture level.

However, for development and testing purposes, full-fledged but lightweight clusters of
different Kubernetes distributions can be set up on the fly even in a single virtual machine.

For example, the [kind](https://kind.sigs.k8s.io/), [k3d](https://k3d.io/stable/), and
[minikube](https://minikube.sigs.k8s.io/docs/) tools
are purposefully designed for creating and spinning up local, *multi-node* K8s
clusters/sandboxes using `docker` with little hassle and resource usage.
These are meant for developers to test Kubernetes distributions on their (isolated)
development machine, but are also suitable for local development, CI, and testing.

The K8s control plane and worker nodes are created as **separate docker containers** based
on specially built docker images, which

- are capable of running arbitrary software modules as preloaded docker images using
  **docker-in-docker**,
- run standard K8s distribution components, e.g., `kubelet`,
- that can be configured via the standard `kubectl` tool from the host machine.

See a detailed description of these tools, their installation and configuration on an
Ubuntu 22.04/24.04 VM in [kubernetes/test](kubernetes/test/README.md).

However, the `ptx-edge` extension's *customer-facing API* can also be separately run in
a single container as a mockup for automated integration test cases.

See further details about Docker-based testing

- in the *Level 1* testing setup [here](kubernetes/test/levels/level1/Makefile)
  with the related [README.md](kubernetes/test/README.md#level-1-testing-mock-api-in-single-docker-image)
- or in the mockup REST-API [README.md](kubernetes/test/mock-api/README.md)
  in `kubernetes/test/mock-api`.

## Running Instructions

To start `ptx-edge` components deployed in the local K8s cluster, run

```bash
make run
```

while for tearing down components, run

```bash
make cleanup
```

> [!IMPORTANT]
>
> Since BB-02 is still under development, Makefile targets currently
> (_setup_ / _run_ / _cleanup_) point directly to the targets of the latest
> readiness level's Makefile in `kubernetes/test/levels`!

These targets launch the deployed `ptx-edge` core services in K8s automatically,
but it does not wait until all the resources are running before it exits!

To check the current status of the installed components, use the following
command:

```bash
$ make status
```

## Example Usage

The `ptx-edge` K8s extension provides a separate _REST-API_ in
[kubernetes/src/rest-api](kubernetes/src/rest-api)
to integrate its features with the PTX core components and to ease the use of
building block services by external APIs or users.

The API uses the [FastAPI](https://fastapi.tiangolo.com/) Python package to implement
its endpoints and also define the related OpenAPI 3 specification directly from the
Python software code.

#### REST-API

- The REST-API uses the following base URL: ``http://<service_name>:8080/ptx-edge/api/v1/``.
- The interactive API interface (**Swagger UI**) lives here: ``http://<service_name>:8080/ptx-edge/api/v1/ui/``
- The OpenAPI specification is available at ``http://<service_name>:8080/ptx-edge/api/v1/openapi.json``

Additionally, the latest OpenAPI specification is auto-generated and updated at every commit
and can be found [here](kubernetes/src/rest-api/spec/openapi.yaml).

#### Testing

For testing purposes, a mock-API is generated based on the BB-02's predefined
[OpenAPI specification](kubernetes/test/mock-api/spec/openapi_design.json).

The detailed description of the mock-API and its internal test cases can be found
in the related [Readme](kubernetes/test/mock-api/README.md).

The REST-API endpoints can be easily tested in the following two approaches:

- Calling directly on the specific endpoint using e.g., ``curl`` and Python's ``json`` module.\
  For example, the standalone [mock REST-API](kubernetes/test/mock-api/README.md)
  can be tested with the following command:

```bash
$ curl -sX 'GET' \
       -H 'accept: application/json' \
       'http://localhost:8080/ptx-edge/api/v1/version' | python3 -m json.tool
{
    "api": "0.1",
    "framework": "0.112.1"
}
```

- Manually testing endpoints with in-line test data on its
  [Swagger UI](kubernetes/test/README.md#rest-api-mockup).

![](docs/swagger_ui_testing.png)

> [!WARNING]
>
> The different `ptx-edge` setups along with the included REST-API service
> may be exposed on different port(s) (e.g., **80**, **8080**, **443**) according
> to the applied (test/dev/prod) K8s setup, used (cloud) load balancer,
> or test VM configuration!
> Refer to the exposed port number in the related part of the documentation!

To execute all module and component tests prepared in the
`kubernetes/test` folder, including all unit tests defined for
each submodule in `kubernetes/src` and explicit component-level
tests, use the joint Makefile target `tests` in the main [Makefile](Makefile):

```bash
$ make tests
```

#### Examples

The following table contains example API calls with successful results.

Further test cases for incorrect input data and other failures are collected in the
mock-APIs unit tests in [kubernetes/test/mock-api/tests](kubernetes/test/mock-api/tests).

To validate the endpoints, send the following requests to the main REST-API using the URL:
``http://<service_name>:8080/ptx-edge/api/v1/<endpoint>``.

| Endpoint                | HTTP verb | Example input (JSON)                                                                                                                                                                                                                                                                                              | Response Code | Example output (JSON)                                                                                                                                                                            |
|-------------------------|:---------:|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-------------:|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| /versions               |    GET    | -                                                                                                                                                                                                                                                                                                                 |      200      | <pre>{"api": "0.1",<br/> "framework": "1.1.4"}</pre>                                                                                                                                             |
| /requestEdgeProc        |   POST    | <pre>{"data": "Data42",<br/> "data_contract": "Contract42",<br/> "func_contract": "Contract42",<br/> "function": "FunctionData42",<br/> "metadata":<br/>     {"CPU-demand": 42,<br/>      "privacy-zone": "zone-A",<br/>      "timeout": 42}</pre>                                                                |      202      | <pre>{"data": "Data42",<br/> "function": "FunctionData42",<br/> "metrics":<br/>     {"elapsed_time": 2,<br/>      "ret": 0},<br/> "uuid": "e09270d1-2760-4fba-b15a-255a9983ddd6"}</pre>          |
| /requestPrivacyEdgeProc |   POST    | <pre>{"consent": "Consent42",<br/> "data_contract": "Contract42",<br/> "func_contract": "Contract42",<br/> "function": "FunctionData42",<br/> "metadata":<br/>     {"CPU-demand": 42,<br/>      "privacy-zone": "zone-A",<br/>      "timeout": 42},<br/> "private_data": "Data42",<br/> "token": "Token42"}</pre> |      202      | <pre>{"function": "FunctionData42",<br/> "metrics":<br/>     {"elapsed_time": 10,<br/>      "ret": 0},<br/> "private_data": "Data42",<br/> "uuid": "a62e865c-a13d-475e-acc1-bce4ff3be66c"}</pre> |

## Test Definitions

Detailed test definitions can be found in [kubernetes/test/cases](kubernetes/test/cases/README.md).

> [!TIP]
>
> All tests can be executed with the `make tests` [target](#testing).

## Unit Testing

Unit tests are based on (Python) module-specific tests defined separately under `kubernetes/src/<module>/tests`
for each `ptx-edge` subcomponent `<module>`.

Since multiple modules use and expose APIs, defined unit tests also contain API endpoint validations.
These test cases usually use specific test methods/dependencies/tools recommended to module's main
framework.

### Setup Test Environment

For installing test dependencies of a given submodule in `kubernetes/src`, refer to the related README file.

Each subproject defines a **Makefile** to unify the development/test environment creation.
Accordingly, test environment configuration (and execution) is implicitly managed by
external tools and third-party libraries, such as
[virtualenv](https://virtualenv.pypa.io/en/latest/),
[pytest](https://docs.pytest.org/en/stable/), and
[tox](https://tox.wiki/en/4.24.1/), within these Makefiles.

Therefore, in general, there is no need for explicit environment setup as it is
automatically configured and managed by wrapper tools/scripts.

However, to explicitly set up the test/dev environment for a `<module>` locally
(without Docker), usually the following command can be used:

```bash
$ cd kubernetes/src/<module> && make setup
```

Furthermore, the configuration of docker-based test environments can be also performed
explicitly by executing the dedicated _Makefile_ target as follows:

```bash
$ cd kubernetes/src/<module> && make docker-test-setup # Preferred way
```

> [!NOTE]
>
> Unit test dependencies are the same as for its main submodules.

### Run Tests

To locally execute all unit tests defined for `ptx-edge`,
use the following helper script in `kubernetes/test/units`:

```bash
$ cd kubernetes/test/units && ./runall.sh
```

For the available configuration parameters, refer to the help menu:

```bash
$ ./runall.sh -h
Usage: ./runall.sh [options]

Options:
    -d          Execute tests in Docker containers instead of local venvs.
    -c          Cleanup projects before build.
    -o <dir>    Collect Junit-style reports into <dir>.
    -h          Display help.
```

To locally execute the unit tests of a single `<module>`,
execute the dedicated _Makefile target_ within the `<module>` folder, e.g.,

```bash
$ cd kubernetes/src/<module> && make unit-tests
```

> [!TIP]
>
> Subprojects may define different dependencies and test parameters
> wrapped by Makefiles. The preferred way for testing is the preconfigured
> <ins>Docker-based test environments</ins>.

For docker-based test execution, use the dedicated `-d` flag of `runall.sh`
or call the dedicated _Makefile target_ of any `<module>`:

```bash
$ cd kubernetes/test/units && ./runall.sh -d    # Preferred way
# or
$ cd kubernetes/src/<module> && make docker-unit-tests
```

JUnit-style test reports are automatically generated and stored in the test containers.
To export these reports from the test environment to the local host/VM, use the `-o` flag
with the `runall.sh` script:

```bash
$ ./runall.sh -d -o results/
[x] Docker-based unit test execution is configured.
[x] JUnit-style reports are configured with path: kubernetes/test/units/results
Preparing report folder...

# <logs truncated>

$ ls -al results/
total 20
drwxrwx--- 1 root vboxsf 4096 Feb 24 20:08 ./
drwxrwx--- 1 root vboxsf 4096 Feb 24 20:01 ../
-rwxrwx--- 1 root vboxsf  218 Feb 24 20:08 report-test-builder.xml
-rwxrwx--- 1 root vboxsf 2878 Feb 24 20:09 report-test-mock-api.xml
-rwxrwx--- 1 root vboxsf  218 Feb 24 20:08 report-test-rest-api.xml
```

### Expected Results

Each component test (script) starting with the prefix `test` is executed successfully
(without `error`/`failure` notification),
while the helper script `runall.sh` returns with value `0`.

An example result log of one successful test execution is the following:

```bash
$ cd kubernetes/test/mock-api
$ make docker-unit-tests

# <logs truncated>

py38 run-test: commands[0] | nosetests -v --with-xunit --xunit-file=report/report-test-mock-api.xml
[66] /usr/src/app$ /usr/src/app/.tox/py38/bin/nosetests -v --with-xunit --xunit-file=report/report-test-mock-api.xml
Test case for checking available live API: HTTP 200 ... ok
Test case for valid   request_edge_proc request: HTTP 202 ... ok
Test case for invalid request_edge_proc request: HTTP 400 ... ok
Test case for invalid request_edge_proc request: HTTP 403 ... ok
Test case for invalid request_edge_proc request: HTTP 404 ... ok
Test case for invalid request_edge_proc request: HTTP 408 ... ok
Test case for invalid request_edge_proc request: HTTP 412 ... ok
Test case for invalid request_edge_proc request: HTTP 503 ... ok
Test case for valid   request_privacy_edge_proc request: HTTP 202 ... ok
Test case for invalid request_privacy_edge_proc request: HTTP 400 ... ok
Test case for invalid request_privacy_edge_proc request: HTTP 401 ... ok
Test case for invalid request_privacy_edge_proc request: HTTP 403 ... ok
Test case for invalid request_privacy_edge_proc request: HTTP 404 ... ok
Test case for invalid request_privacy_edge_proc request: HTTP 408 ... ok
Test case for invalid request_privacy_edge_proc request: HTTP 412 ... ok
Test case for invalid request_privacy_edge_proc request: HTTP 503 ... ok
Test case for valid   get_versions response: HTTP 200 ... ok

----------------------------------------------------------------------
XML: /usr/src/app/report/report-test-mock-api.xml
----------------------------------------------------------------------
Ran 17 tests in 3.709s

OK
_____________________________________________________________________________________________________ summary _____________________________________________________________________________________________________
  py38: commands succeeded
  congratulations :)
```

Programmatically, each Makefile returns the value `0` in case all executed tests defined in the target
`unit-tests` were successful, and a non-zero value otherwise.
The helper script `runall.sh` follows this "UNIX" behavior as well.

> [!NOTE]
>
> Detailed test execution summary can be found in
> [kubernetes/test/suites/README.md](kubernetes/test/suites/README.md#test-execution-summary).

## Component-Level Testing

Testing of `ptx-edge` components is based on the basic functionality and applicability of
`ptx-edge` _K8s components_ defined in the [Design document](#design-document).
This means that the designed component-level tests aim to test

- [K8s manifest files](kubernetes/test/manifests/) designed to be used as templates by `ptx-edge` modules,
- Implicitly validate K8s capabilities and K8s API server endpoints on which `ptx-edge` modules rely,
- Interactions between `ptx-edge` modules as well as with K8s entities (services, persistent volumes, load balancer,
  etc.).

The related test cases can be found in [kubernetes/test/suites](kubernetes/test/suites).

> [!NOTE]
>
> For the detailed description of component-level tests, refer to the
> related [README.md](kubernetes/test/README.md#tests).

Typically, these test scripts perform the following steps:

- set up and configure a **K3s test environment** according to the test case,
- deploy <ins>test manifest file(s)</ins> or make direct configuration by using <ins>K8s API</ins> using `kubectl`,
- wait for component(s) to set up and reach a **stable state** or **escalate designed issues**,
- check the test status and validate the outcome, and
- tear down the test environment.

### Setup Test Environment

To install test dependencies with the latest versions:

```bash
$ cd kubernetes/test/suites && ./install-dep.sh -u
```

> [!WARNING]
>
> For test report generation, the flag `-u` is mandatory!

### Run Tests

To execute all component-level tests with **JUnit-style** test report generation (into the folder
`kubernetes/test/suites/results`), use the following helper script:

```bash
$ cd kubernetes/test/suites && ./runall.sh -o ./results
[x] JUnit-style reports are configured with path: kubernetes/test/suites/results

Preparing report folder...

# <logs truncated>

$ ls -al results/
total 20
drwxrwx--- 1 root vboxsf 4096 Feb 20 16:56 .
drwxrwx--- 1 root vboxsf 4096 Feb 20 12:31 ..
-rwxrwx--- 1 root vboxsf  445 Feb 20 16:56 report-test-policy-zone-scheduling.xml
-rwxrwx--- 1 root vboxsf  524 Feb 20 16:59 report-test-ptx-edge-builder.xml
-rwxrwx--- 1 root vboxsf  265 Feb 20 17:00 report-test-ptx-edge-rest-api.xml
```

For the available configuration parameters, refer to the help menu:

```bash
$ ./runall.sh -h
Usage: ./runall.sh [options]

Options:
    -o <dir>    Generate Junit-style reports into <dir>.
    -h          Display help.
```

### Expected Results

Each component test script starting with the prefix `test` in the folder `kubernetes/test/suites`
is executed successfully (without `error`/`failure` notification),
while the helper script `runall.sh` returns with value `0`.

An example result log of one successful test execution is the following:

```bash
$ ./test-policy-zone-scheduling.sh -- testPolicyZoneSchedulingWithNodeSelector

# <logs truncated>

Ran 1 test.

OK
```

Programmatically, each test script returns `0` in case all defined test
cases were successful, and a non-zero value otherwise.
The helper script `runall.sh` follows this UNIX behavior as well.

> [!NOTE]

> Detailed test execution summary can be found in
> [kubernetes/test/units/README.md](kubernetes/test/units/README.md#test-execution-summary).
