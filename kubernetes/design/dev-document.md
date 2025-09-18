# Technical Documentation

## Overview

The **Edge Computing BB** primarily provides a common platform to execute simple stateless function logics,
standalone data (pre-)processing components, or other containerized (parts of) PTX building blocks in an
(edge) cloud environment, while taking cloud-native and dataspace-related privacy concerns into account.

The BB is fundamentally based on the open-source [Kubernetes orchestrations framework](https://kubernetes.io/)
(K8s) that inherently provides advanced levels of 

 - scalability,
 - flexibility,
 - resiliency,
 - and portability

with respect to the actual execution of data processing components. The BB is fundamentally designed to be
integrated with the PTX dataspace, while introducing a high-level privacy concept of geographically-distributed
(edge-cloud) dataspaces, incorporating multiple **Privacy Zones** and a dedicated data provider role of 
**Function Providers**. For the detailed concept, goals, and benefits of Edge Computing BB, see the accompanied
[Design Document](../../docs/design-document.md).


## Design Principles

One of the main benefits of the edge computing BB is that their components, behaving as standalone
[microservices](https://microservices.io/), are designed with generality and reusability in mind and
with the least amount of external dependencies and tools as possible.
Thus, all of these BB components together offer a multipurpose platform for executing data consuming,
processing, and transforming pieces of software (such as
[ETL processes](https://en.wikipedia.org/wiki/Extract,_transform,_load))
anywhere a Kubernetes orchestration framework can be deployed and operated.

These generality and portability design principles allow for extending the BB's usability to be deployable
not just in multi-cloud edge environments, but also in a single-node hosted server with public accessibility
(e.g., [k3s](https://k3s.io/) deployed on a single VM) or in a (multi-node) emulated K8s environment
configured on a single laptop (e.g., using docker with [k3d](https://k3d.io/stable/) or kind).
Accordingly, the installation steps is unified for all K8s-based environments by relying on [containerized
BB components](../src) built and assembled during installation time and common K8s manifest files
and [Helm charts](https://helm.sh/).
Since the Edge Computing BB's component do not build on external tools and APIs other than the basic
features of the vanilla Kubernetes (>=v1.33), it provides high-levels of flexibility and portability.


### Cluster Topology

In practice, the _Privacy Zone_ (PZ) is represented as a specific label assigned to compute nodes that belong
to the corresponding privacy zone. The following rules apply to the PZ configuration of a K8s cluster.

 - Each PZ has a dedicated node label in the cluster, which can have the value _"true"_ or _"false"_ (default).
 - One node can belong to one or more privacy zones.
 - One privacy zone can consist of one or more cluster nodes.
 - In each privacy zone, one cluster node is designated as the zone leader (by a dedicated node label).
 - One node can be marked as zone leader for multiple privacy zones that the node belongs to.

Currently, the PZ assignment uses the label `privacy-zone.dataspace.ptx.org/{zone-id}=true` where `zone-id`
is the unique identification of the privacy zone in the cluster, while the zone leader role is marked with
the label `connector.dataspace.ptx.org/enabled=true`.

In single-node environments, where there is only one cluster compute node, the topology configuration 
automatically assigns the default zone id `zone-0` and its zone leading role to the single node.
By this way, the Edge Computing BB can be used over multiple infrastructure, while providing implicit
scalability and extendability by default.

The default scheduler of K8s can take the zone labels to deploy component in the corresponding privacy 
zones, thus offering privacy guarantees for data processing tasks. This functionality is extended by the
custom scheduler modul of the Edge Computing BB in order to also consider dataspace-originated privacy
demands as well as data transmission delays beside the de facto scheduling metrics of compute, memory,
and storage.


#### Privacy Preserving Processing

Accordingly, each privacy zone has one PDC instance that is responsible for the communication with the
PTX components (catalog, consent, and contract manager), and the temporary caching of exchanged private
data in its dedicated mongo database. For this reason, PDC instances are bound to the zone leader nodes.

In other terms, each privacy zone leader runs a PDC instance serving the data consuming workers in the
corresponding privacy zone(s), since a (leader) node can belong to multiple privacy zones. Currently, this
feature relies on the **node selector** and **affinity/anti-affinity** rules of K8s deployments, essentially
using the specific zone labels as filters. This K8s-based node filtering approach offers high-level
flexibility on the expressing of privacy zone restriction, such as designating one or multiple feasible
zones, or even excluding a zone from the feasible zones. Since in one privacy zone multiple cluster nodes
can be feasible choices for scheduling, the custom scheduler have to select the node from the cluster,
which has sufficient compute resources and involves an appropriate data migration workflow from the
dataspace/privacy perspectives.


#### Efficient Near-Data Processing

The near-data processing mode basically restricts the node selection task to choose a feasible node that
involves the least amount of data migration. To this end, the default K8s scheduler can be configured
to use the zone leader label as the node filter, and therefore, place the data consuming worker right
next to the corresponding PDC instance at the same cluster node.
In other terms, this node selection strategy enforce the worker process to be co-located with the PDC
instant and its internal mongo database, which means the data migration can be performed locally within
the cluster node and reducing the transmission delay as well as the introduces privacy concerns to the 
minimum. In addition, the custom scheduler component extends this colocation restriction to consider
feasible cluster nodes close to the leader node (PDC instance) in case there is no sufficient compute
resource available at the zone leader node.

In emulated/single-node K8s environments, the scheduler always selects the only available, default cluster
node in the default privacy zone in both processing modes. This means that no change is required in the
Edge Computing components whether it is used over single/multi-node or distributed/emulated clusters.

### External Resources

The Edge Computing BB expects the configurations of two external resources for the private dataset 
(**datasource**), on which some tasks should be executed, and the (containerized) data consuming software
(**worker**) that actually implements and encompasses the data processing logic.
The Edge Computing BB is designed to understand, collect, and prepare the execution of worker task from
different sources. See the options in detail in the description of
[Edge Computing Components](#edge-computing-components).
It also uses the latest version of 
[PTX Dataspace Controller](https://github.com/Prometheus-X-association/dataspace-connector) (PDC) for 
collecting datasource/worker configuration (e.g., credentials of repositories storing the raw data)
via the PTX dataspace.

By design, the worker logic, as a standard ETL task, is assumed to be a standalone stateless software
or component that can be executed in a container that expects the private data as a local file(s),
completes its execution within a predictable time, and preferably stores the results in another 
local file. Accordingly, the initiator of the worker task can pull the status of the task and collects 
the results in poll mode.
However, also a long-running mode is under development where the initiated worker logic, as a long-running
process not a job/task, can run for indefinite time, collect data from it s data source continuously, and
can be terminated by the initiator explicitly (see in development features).
The worker logic can be as complex as its developer want to be provided it can be packaged in a container
(or in multiple containers, see future works features) and can be configured in K8s-compatible way, that is,
using command line parameters or environment variables.

### Building Blocks

The implemented K8s-based components of the Edge computing BB fully covers the high-level concepts and
building block of the designs document, which are summarized in following schematic diagram:

![Kubernetes_ref_architecture.png](Kubernetes_ref_architecture.png)

This description is meant for providing a deep-dive system-level perspective about the actual implementation
of these BB components as well as giving a comprehensive view of how these components work and what are their 
purposes and responsibilities. The description is also incorporates the status of these components' development
phase and denotes the short-term planned improvements and long-term future works.

Currently, the detailed technical documentation of these components' elements along with their input/output
formats can be found along with the source code as inline documentation.

### Deployment Environment

The development/testing environment relies on the **k3d** tool that can deploy and initiate a low-footprint
variant of the Kubernetes framework called **k3s** with implicit load balancing, image registry, ingress control,
and reverse TLS terminating features. This tool is capable of emulating a multi-node Kubernetes cluster based
on specific docker images, where each "physical" node is played by a docker container, and uses *docker-in-docker*
features to execute pods/containers. This emulated environment can be also used in production environment,
which despite the additional overhead of the introduced abstraction layer can provide benefits such as
implicit independence of the underlying Kubernetes variant, unified deployment process, and better testability.

The only particular Kubernetes specifics that the Edge Computing BB depends on is the actual implementation
and configuration of k3s' Ingress Controller provider that build on **[traefik](https://traefik.io/)**.
Essentially, the BB's deployment process must be adjusted in case the target K8s deployment uses other 
than traefik for the underlying load balancer / application proxy, more precisely, the application routing
for the PDC instances and the BB's REST-API.

This is currently the only deployment-specific part of the BB, as PDC does not support subpath handling
(although it can allow to configure subpath in its endpoint setting) and the standart K8s Ingress 


## Edge Computing Components

### [deployment](../deployment)

### [builder](../src/builder)

### [operator](../src/operator)

### [ptx](../src/ptx)

### [registry](../src/registry)

### [rest-api](../src/rest-api)

### [scheduler](../src/scheduler)

### [samples](../src/samples)

### [test](../test)