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
[kubernetes/design](kubernetes/design/) folder.

## Building instructions
_Describe how to build the BB._

E.g.: `docker build -t <bb name>:latest .` or `npm install` 

## Running instructions
_Describe how to run the BB._

E.g.: `docker compose up` or `npm run`

## Example usage
_Describe how to check some basic functionality of the BB._
E.g.:

Send the following requests to the designated endpoints:
| Endpoint      | Example input | Expected output   |
| ------------- | ------------- | ----------------- |
| /hello        | World         | 200, Hello World! |
|               |               |                   |
|               |               |                   |
