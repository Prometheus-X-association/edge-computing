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
features of the vanilla Kubernetes (>=v1.31), it provides high-levels of flexibility and portability.

In contrast to plain docker-compose based deployment setups, Kubernetes, as a mature, continuously developed, 
and widely used container orchestration platform implicitly provide advantages for running worker tasks and 
components both from compute and privacy perspectives, such as
 - compute resource quotas,
 - load balancing and parallelization.
 - role-based access control (RBAC),
 - inbound/outbound network policies, 
 - implicit TLS termination proxy, etc.

In addition, the Edge Computing BB offers native integration with the 
[PTX Dataspace Controller](https://github.com/Prometheus-X-association/dataspace-connector) (PDC) to communicate
with dataspace core components and manage sensitive data exchange.
The BB uses a slim variant of the connector, for which the dependencies are prebuilt in its base container image,
and its configuration, including the endpoint url, session secrets, credentials, port number, etc., can be set
during initialization time using environment variables. 
The PDC instance also associated with a dedicated Mongo database (in one pod) for storing intermediate data
and configuration values.
It can communicate with the outside world through the cluster's single gateway, where each instance is
differentiated by their privacy zone, whereas the PDC's main API is also exposed on the hosted cluster node
for direct communication.
Thus, a PDC deployment is absolutely independent of other PDCs running in the same cluster, which ensures that
each privacy zone has a dedicated interface for the PTX dataspace, through which every communication steps, 
private data exchange, and network traffic occur only either between the PTX core and PDC components or in
the permitted privacy zone.


### Cluster Topology

#### Privacy Zone

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
It also uses the latest version of PDC for collecting datasource/worker configuration (e.g., credentials
of repositories storing the raw data) via the PTX dataspace.

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
(although it can allow to configure subpath in its endpoint setting) and the standard K8s Ingress 


## Edge Computing BB Components

Following the cloud native/microservices 

### [deployment](../deployment)

The deployment section contains the specific deployment automatization and configuration scripts for the
different platforms.
The deployment steps of the building block components require the following high-level steps:
 - (Compile), Assemble, and build the components' container images locally as currently there is no dedicated
repository for the component images.
 - Configure the K8s cluster access method and rights, or create an emulated K8s cluster locally(, which
usually configure the cluster access by default.)
 - Deploy and configure the components within the cluster, such as namespace/volume creation, deployment/service
initiation, RBAC role definition and binding, ingress route configuration, etc.

Basically, the whole deployment process uses the `config.sh` to define environment variables (envvar) as
config parameters, while the `setup.sh` defines the basic installation steps, specifically the 
 - cleanup, 
 - image building,
 - environment creation using k3d, 
 - default certificate generation,
 - cluster configuration, 
 - copying images inside the cluster,
 - and component installation steps.

The setup script uses the `envsubst` tool to read manually created manifest templates from the `templates`
folder and substitute the configuration variables for deployment.

The sensitive parameters, such as usernames, passwords, public IPs, secrets and keys are defined in a 
separate file `cluster-creds.sh` under the folder `.creds`. It also defined a `Makefile` for convenience.


#### PTX Dataspace Connector (PDC)

Basically, the PDC is deployed as a _K8s Daemonset_ with a specific node filter on the zone leader nodes. 
The PDC controller is configured using a _K8s ConfigMap_ that defines 

 - a config file template for storing production configuration values in _JSON format_, 
 - non-sensitive configuration values, such as the catalog's URI, etc., that are provided for the connector as envvars,
 - and an inline `entypoint.sh` init script that generates the actual config file `config.production.json`
 using the tool `envsubst`.

The sensitive configuration values, such as the secret key, is provided as a _K8s Secret_.
The PDC pod consists of two containers, one for the actual connector tool and a _[MongoDB](https://www.mongodb.com/)_
database with pinpointed version.
These configuration options are automatically mounted in the connector's own container.

The PDC deployment also extended with an **init container**, implemented as a standalone feature of the 
builder component, in order to prepare and set up the PDC's environment and accessibility.
It uses the Kubernetes main API to list, create, and patch K8s objects dynamically. 
For security reasons, a specific service account is created for the PDC instances, though which the automatic
mount of the K8s API credentials are disabled, whilst the API token and other config parameters as a manually
prepared **projected volume** are explicitly mounted only into the init container to realize restricted access to K8s
services.
Fundamentally, the init script support two approach to separate and make the PDC instances available within the 
cluster as well as from outside the cluster, while circumvent the limitations of K8s deployments, e.g.,
differentiating deployed pods within a daemonset or duplicating node labels in pod metadata.

In the **headless** approach, the init script collects the internal node IP addresses to create _K8s Services_ 
dynamically for each privacy zone/PDC instance, which have no dedicated virtual IP valid within the cluster,
but directly point to the connectors' ports allocated on the assigned cluster nodes.
This requires the lowest level of K8s API privileges for creating PDC services per privacy zones, which build on a
single entry point (port) to access to the connector without knowing the hosting node's IP address.
Unfortunately, these setup is incapable of publishing these PDC services through the ingress controllers configuration
as K8s Ingress does not support proxying traffic through the ingress port to services without virtual cluster IPs.

Therefore, the **clusterip**-based approach is designed to dynamically check and collect privacy zone labels of the
node the daemonset's pod is scheduled on and create PDC instance services for nodes using the unique zone labels as
selectors. Although this service creation approach fit the best to the cloud native principles of Kubernetes, 
it requires a wider range of access rights and the on-the-fly patching of the daemonset's main pod in which
the init container is executed.

#### Ingress 

The implicit **K8s Ingress** controller is basically configured to use TLS-based secure tunnelling for the HTTPS
communications and follows the standard approach of binding specific endpoints to dedicated services in front of
the deployed Edge Computing BB.
By design, the REST-API and each deployed PDC instances are configured to use different URL paths for traffic
separation using the HTTP prefixes `<PTX namespace>/api/v1` and `<PTX namespace>/<privacy zone ID>/pdc`, respectively.

Since the PDC's configuration only allows for defining subpaths for the PTX-related `endpoint`, but not for the
PDC API itself, the PDC ingress routes are extended with additional _subpath stripping_ configuration options.
Unfortunately, this kind of path manipulation features are not natively available in K8s specification, but are
usually supported by the underlying application proxy modules, such as in the case of
[traefik](https://doc.traefik.io/traefik/reference/routing-configuration/http/middlewares/stripprefix/) 
or [Nginx](https://github.com/kubernetes/ingress-nginx/blob/main/docs/examples/rewrite/README.md).
Thus, these configuration option represents the only implementation/platform dependents settings of the
Edge Computing BB.

#### TLS Termination Proxy

The TLS-related configuration along with the exposed cluster ports are defined in an auxiliary manifest
that is automatically processed by K3s at initialization time.

**[In Development]**

Instead of manually-written and maintained shell scripts, the components' installation and configuration
can be implemented using **[Helm charts](https://helm.sh/)**, which is the de facto approach of K3s application
packaging and distribution.
This also requires the use of the specific go-templating in the base manifests and the definition of config
parameters in different `values.yaml` files.

Although the underlying _traefik_ application proxy, which is used by the k3s, provides a simple and 
convenient way for enabling dynamic TLS certificate generation and renewal based on Letsencrypt/ACME,
this is inherently tied to the traefik's implementation and reduces the portability of the Edge Computing
BB between different K8s clusters.
One more general way for handling certificate independent of the ingress controller's implementation is using
a dedicated certificate management service, such as **[cert-manager](https://cert-manager.io/)**.
`cert-manager` provides a common approach for cloud native certificate management, where TLS certificates is
stored in K8s Secrets that can be given for direct application in the ingress routing configuration using
(multiple) K8s manifests.
Implicitly, in this case, the TLS configuration is moved from the low-level application proxy/ingress controller
(k3d cluster configuration) on a higher level (k8s service configuration).

**[Future Work]**

Since the development of [Kubernetes Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/)
is stopped in favor of the more general and versatile features
of **[Kubernetes Gateway API](https://gateway-api.sigs.k8s.io/)**.
Although Gateway API features provides a more flexible approach, its applicability requires further
considerations due to its more complex configuration and still relatively early stage of development in
contrast to the widely supported and mature feature of K8s Ingress.
Important to note that the TLS-based, secure HTTP route configuration with K8s Gateway API typically requires
external certificate management configuration (at least in case of the traefik proxy),
e.g., based on the _cert-manager_ package.

Thus, the support of K8s Gateway API requires the support of cert-manager as a prerequisite.


### [builder](../src/builder)

The builder implements one of the core (dynamicity) feature of the Edge Computing BB.
Similar to the PDC's init container approach, it is executed before the main container of the worker task job
and is responsible for 
 - collecting the private/raw `data`, typically as a compressed file(s), from different locations and protocols,
 - collecting the `worker` environment as a container image,
 - and configure its own deployment config, including pod/job description, on the fly.

The builder uses a base configuration file and envvars to merge the configuration options into a global object,
based on which the resource collection methods are initiated.
In most configuration options, the data/worker source designates the actual source and collection method/protocol
of the given resource, while additional config options define the configurations of the access method, such as
username/password pairs and credentials.

#### Data Resource

The following private data source options are supported:
 
- `file://`: The given file mounted in the container or originally available in the builder container image is 
    simply copied into the data destination (dst) that is accessible from the worker container.
- `http://` and `https://`: Collect data files via HTTP from a remote server.
  Use other config options to consider authentication schemes and username/password pairs, etc. 
- `ptx://`: Collect data source configuration from the PTX dataspace.
    Use other config options to define PTX offer IDs and can parse received data for inline source configuration
    and forward the data collection workflow with other aforementioned methods.

The following worker source options are supported:

- `docker://`: Configure the worker container image to use an internal image which is collected from a remote
    docker registry and pushed into the local registry with a predefined name.
    Use other config options to consider authentication username/password pairs.
- `secret://`: Configure the worker container image to use a _K8s Image Pull Secret_, for which the credentials
    are given in other config options.
- `ptx://`: Collect worker configuration from the PTX dataspace.
    Use other config options to define PTX offer IDs and can parse received data for inline source configuration
    and forward the data collection workflow with other aforementioned methods.

### [operator](../src/operator)

TBD

### [ptx](../src/ptx)

The `ptx` folder contains the container image description files (e.g., Dockerfile) and test materials
along with inline Makefile commands to build and assemble low-footprint, K8s-conformant PDC and sandbox
components that have 
 - prebuilt dependencies for faster container startup times,
 - altered base image types and dependencies for lower image sizes, and 
 - tailored entrypoint scripts to realize init-time configuration capabilities using envvars.

Variables in the provided [Makefile](../src/ptx/Makefile) define the considered connector components
and the applied PDC and MongoDB versions.

The schematic steps of the PTX build processes are the following.
 - Clone the PDC source from the official
    [GitHub repository](https://github.com/Prometheus-X-association/dataspace-connector)
    into a temporary folder
 - Switch to the specific branch denoted by the defined PDC version, e.g., `PDC_VER := 1.9.7`
 - Copy the altered resource materials into the cloned git repository
 - Build the connector, mongodb, and sandbox components using the tailored Dockerfiles
 - Delete the temporary folder

These Dockerfiles are typically based on alpine-linux images and incorporate dependencies, pre-assembled
resources, and materials to make the container more or less self-contained regarding the necessary config
steps, define and fix component versions, and reduce container startup times as low as possible.

### [registry](../src/registry)

This repo contains the construction steps for creating an image registry for the used K8s cluster.
Initially, it creates (self-signed) certificate, including a top-level CA certificate, an intermediate
certificate signing request, and an X.509 certificate with alternative DNS names, for secure TLS-based 
communication between cluster nodes and the registry.
The registry is meant for storing the component container images of the Edge computing BB.
Each cluster node is configured to know the authentication credentials for pulling the component 
images seamlessly when the BB is deployed in the cluster.

The registry builds on the docker's standard [registry image](https://hub.docker.com/_/registry)
(v3) that also configured to use the generated certificates and a predefined username/password
using the tool `htpasswd`.

In the locally emulated `k3d`, the self-managed registry functionality is provided and managed by 
default, while the registry authentication configs are defined for the underlying `k3s` Kubernetes
in the cluster description manifest. For performance reasons, the uploaded container images caches
are hosted on the host platform by pre-mount folder (`/var/lib/registry`).

**[Future Work]**

In other cases, the assembled registry can be used as an internal cluster service initiated as a
pod in the cluster itself, or as an external service managed by other partner(s).
Since the registry can be run in standalone mode without any modification in its basic configuration,
the provisioning of the internal registry can be supported by a single K8s deployment manifest or
docker compose file, along with their configuration options.
However, these options require network and application-level configuration steps (e.g., bridged docker
network and proper DNS entries) as (the kubelet process on the) cluster nodes must have access to the
internally/externally managed registry container/pod. 

### [rest-api](../src/rest-api)

The rest-api contains the [FastAPI](https://fastapi.tiangolo.com/)-based server for hosting the RESTful
interface of the Edge Computing BB for other partners to 

- initiate dynamically assembled jobs
- acquire the status of the worker processes
- obtain the result of the worker

**[In Development]**

Since the development of the BB follows a bottom-up development approach, thus the current focus is on
the fundamental deployment features of the builder/worker concept.
Thus, the high-level features of the BB's public interface will be implemented as the last step of the
development process.

### [scheduler](../src/scheduler)

The custom scheduler component is meant for advanced pod assigment to cluster nodes based on the
PTX dataspace configurations, such as number of privacy zones, the location of zone leaders, or
the compute and network level metrics.

The default K8s scheduler is capable of considering privacy zone and leader node labels for node
selection using its node selector and affinity/anti-affinity features. Although, it cannot take
dataspace-specific metrics into account.

The default custom scheduler behavior (`random`) is a very rudimentary approach mainly for testing
purposes. It simply chooses a randon node from the available nodes without compute resource quotas.
This is only a valid options in emulated cluster environments, where cluster nodes has full access
to the underlying host resources and the number of worker tasks are reasonably limited.

It builds on the standard K8s ways for defining custom schedulers using a dedicated service account
for fine-granular RBAC control.

**[In Development]**

The dataspace-related scheduling algorithm is meant for incorporating the dataspace concept into
the scheduling decisions.

### [samples](../src/samples)

The `samples` folder contains two similar, deployable example jobs that use the `ptx-edge` k8s package
and its dynamic builder/worker approach to collect raw data from a remote location and train a specific
machine learning model on them.
The compressed evaluation test datasets can be found in a separate subfolder [datasets](../src/samples/datasets).

The container images are given with Dockerfiles that rely on standard python base images, copy
the training source code, and install the dependencies of the applied ML model and framework.
The container images should be pre-built locally before testing. 

The two example project is the following:

#### [ConvNet](../src/samples/convnet)

The application uses the [Keras](https://keras.io/) python framework to train a _deep convolutional neural network_ (CNN)
model based on `Keras`' [MNIST digits classification dataset](https://keras.io/api/datasets/mnist/).

#### [GBC](../src/samples/gbc)

The application uses the [scikit-learn](https://scikit-learn.org/stable/) python package to train a _Gradient Boosting Classifier_ (GBC) machine learning
model based on `sklearn`'s [Olivetti faces dataset](https://scikit-learn.org/stable/datasets/real_world.html#the-olivetti-faces-dataset).

### [test](../test)

The `test` folder contains all the required resources, materials, test manifests, and scripts for unit and
integration testing.

See the detailed description in [test/README.md](../test/README.md)