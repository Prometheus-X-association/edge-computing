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
See the design document [here](docs/design-document.md).

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
