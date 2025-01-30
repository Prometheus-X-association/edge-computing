# Edge computing - AI processing BB

The *Edge Computing (Decentralized AI processing) BB* (BB-02) provides value-added services
exploiting an underlying distributed edge computing infrastructure (e.g., owned and operated
by Cloud Providers).

Two main high-level objectives are targeted by these services:

- **Privacy-preserving**, where data is kept close to the user, more exactly within a pre-defined
privacy zone.
- **Efficient near-data processing**, with optimized performance and resource utilization.

In general, the main goal is to move (AI) processing functions close to the data source
and execute them on-site. If the execution capability is available on-site, that is, in the
virtual/physical node storing the data, the data-consuming software function (as a FaaS
based operation) or container (as a CaaS based operation) is launched there (e.g., by a 
Kubernetes-based orchestration framework). Thus, we can avoid the transmission of a large
amount of data and address privacy challenges designated by geographical or provider-related
rules and demands.

As a more realistic scenario, the data can also be moved for processing but only within a
pre-defined **privacy zone**. This privacy zone primarily encompasses a set of worker nodes
(using the Kubernetes terminology), that are suitable in the sense of pre-defined privacy
rules and where processing functions can and should be deployed on demand.

## Design Document

See the comprehensive design document [here](docs/design-document.md).

Since the functionalities of the Edge Computing BB fundamentally rely on the **Kubernetes**
container orchestration platform (realistically spanning multiple providers' domains/clouds), 
its value-added services are implemented as standalone software containers, operated in a 
dedicated Kubernetes namespace, and several PTX-tailored extensions of the Kubernetes framework itself.

The main components of the BB-02's functionality cover the following:

- Provide a generic runtime environment for data-processing functions.
- Provide the ability to deploy pre-built containers with privacy-preserving options.
- Provide the capability of managing and orchestrating by privacy-zone labels.
- Use the PTX Connector to interact with PTX core elements.
- Implement and control the process of obtaining data for data consumer functions/software.
- Implement a separate REST-API interface for the integration with PTX dataspace.

See the retailed Kubernetes-based architecture design in
[kubernetes/design](kubernetes/design) folder.

## Building instructions

### Production

Since BB-02 is basically a set of extensions to the Kubernetes framework, instead of 
standalone containerized software modules, its installation and setup require different
steps, and most of all, *an operating vanilla Kubernetes cluster* as a prerequisite.

There are many methods and tools for setting up a production-grade Kubernetes cluster on
a local machine, see for example the Kubernetes'
[official documentation](https://kubernetes.io/docs/setup/), or pick any of the numerous
[certified platforms](https://kubernetes.io/docs/setup/production-environment/turnkey-solutions/)
or managed cloud services available online.

The installation and configuration steps are grouped together into separate helper scripts with 
a dedicated [Makefile](Makefile), which internally use dedicated Kubernetes packages 
called [Helm charts](https://helm.sh/).

To install the dependencies and the **ptx-edge extension** assuming a default `kubectl` 
profile for a running Kubernetes cluster, use the following instruction:
```bash
make install
```

or execute the helper scripts directly:
```bash
# TBD
```

or install necessary resources/dependencies and the ptx-edge Helm charts
manually:
```bash
# TBD
```

### Development & Testing

> [!IMPORTANT]
> 
> The BB-02 module is unique in that sense that it cannot be seamlessly run by a 
> container framework, such as Docker or Podman, as it is inherently based on container 
> orchestration features of higher architecture level.

However, for development and testing purposes, full-fledged but lightweight clusters of
different Kubernetes distributions can be set up on the fly even in a single virtual machine.

For example, the [kind](https://kind.sigs.k8s.io/) and [k3d](https://k3d.io/stable/) tools
are purposefully designed for creating and spinning up local, multi-node K8s clusters/sandboxes
using `docker` with little hassle and resource usage.
These are meant for developers to test Kubernetes distributions on their (isolated)
development machine, but are also suitable for local development, CI, and testing.

The K8s control plane and worker nodes are created as **separate docker containers** based
on special-built docker images, which 

- are capable of running arbitrary software modules as preloaded docker images using
  **docker-in-docker**,
- run standard K8s distribution components, e.g., `kubelet`,
- that can be configured via the standard `kubectl` tool from the host machine.

See detailed description of these tools, their installation, and configuration for `ptx-edge` 
in [kubernetes/test](kubernetes/test/README.md).

## Running instructions

The installed Helm chart launches the included `ptx-edge` services automatically,
but it does not wait until all the resources are running before it exits.

To check the current status of the installed chart's components, use the following
command:
```bash
# TBD
```

To keep track of a release's state, or to re-read configuration information, you can
use
```bash
# TBD
```

## Example usage
_Describe how to check some basic functionality of the BB._
E.g.:

Send the following requests to the designated endpoints:
| Endpoint      | Example input | Expected output   |
| ------------- | ------------- | ----------------- |
| /hello        | World         | 200, Hello World! |
|               |               |                   |
|               |               |                   |
