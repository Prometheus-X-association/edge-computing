# Test Definitions

Test case definitions are primarily designed for defining and describing the multi-level
validation process of the `ptx-edge` K8s extension covering the following three aspects:

- Suitability and functionality of the standalone `ptx-edge` components.
    - Verification of component configuration, deployment, and execution.
- Applicability of `ptx-edge` in the **K8s** and **PTX** environments.
    - Verification of API communications (internal/K8s downward API, PDC API).
- Conformity of `ptx-edge` to its main high-level goals:
    - Privacy-preserving AI/data processing
    - Efficient near-data processing

The high-level test specification of `ptx-edge` is provided in the
[design document](../../../docs/design-document.md#test-specification).

> [!IMPORTANT]
>
> Since the _Edge computing - AI processing BB_ (`ptx-edge`) is still
> **under development**, the defined test cases only cover the implemented
> parts of `ptx-edge`'s planned capabilities.
>
> Further test cases are expected to be added continuously.

## Test case definitions

### API-related tests

#### Setup

Use the **level3** [Makefile](../levels/level3/Makefile)
or the main [Makefile](../../../Makefile) in case its internal `TEST_LEVEL` variable points to `level3`.

> [!TIP]
>
> The main Makefile's test level can be overwritten from CLI
> by setting an environment variable with the same name (TEST_LEVEL).

```bash
$ cd kubernetes/test/levels/level3 && make setup run
# or
$ make TEST_LEVEL=level3 setup run
```

To tear down the test environment, use

```bash
$ make cleanup
```

The API service with the preconfigured version (`ptx-edge/rest-api:0.1`) is initiated
in a local test K8s cluster (`ptx-edge-test`) within the namespace `ptx-edge`,
along with kind's `cloud controller manager` providing an external load balancer
service for the co-deployed `nginx`-based ingress controller.

To validate the environment setup, use the following commands:

```bash
# containers: kindest/node, cloud-controller-manager, and envoyproxy are up and running
$ docker ps | grep kind
# rest-api deployment is ready with all pods completed/running 
$ kubectl -n ptx-edge get all
# ingress-nginx deployment is ready with all pods completed/running 
$ kubectl -n ingress-nginx get all
# ingress is configured with bound address
$ kubectl -n ptx-edge get ingress
```

#### Execution

To execute a test call on the REST-API service (based on`ptx-edge/rest-api:0.1`),
use the command below with the predefined input JSON template.

```bash
curl -X 'POST' 'http://<service_ip>:<port>/ptx-edge/v1/<endpoint>' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "data": <data_id>,
    "data_contract": <data_contract_id>,
    "func_contract": <func_contract_id>,
    "function": <function_id>,
    "metadata": {
        "CPU-demand": <cpu>,
        "privacy-zone": <pz_id>,
        "timeout": <timeout>
    }
}'
```

The input template defines the following parameters:

- _API-related parameters_:
    - **service_ip**: IP address of the exposed service — Check the `make` log
      for the dynamically assigned (kind/docker) node IP on which the REST-API is exposed
      (typically, but not exclusively from **172.18.0.0/16**).
    - **port**: service port - `nginx-ingress` expose service both on port **80** and **443**.
    - **endpoint**: REST-API endpoint subject to the current test case.
- _PTX-related parameters_:
    - **data_id**: see in the [design document](../../../docs/design-document.md#input--output-data)
    - **data_contract_id**: see in the [design document](../../../docs/design-document.md#input--output-data)
    - **function_id**: see in the [design document](../../../docs/design-document.md#input--output-data)
    - **func_contract_id**: see in the [design document](../../../docs/design-document.md#input--output-data)
    - **function_id**: see in the [design document](../../../docs/design-document.md#input--output-data)
- _Deployment (K8s)-related parameters_:
    - **cpu**: resource requirement of the function implementation
    - **pz_id**: Privacy zone restriction, see in
      the [design document](../../../docs/design-document.md#input--output-data)
    - **timeout**: execution requirement

In the case of accepted invocation and function deployment, the API responds a predefined
JSON output of deployment metadata with HTTP code **2xx**.

In other unsuccessful cases, the API responds with an HTTP code **4xx** or **5xx**.

| Example Input                                                                                                                                                                                                                                      | Example Output                                                                                                                                                                          |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| <pre>{"data": "Data42",<br/> "data_contract": "Contract42",<br/> "func_contract": "Contract42",<br/> "function": "FunctionData42",<br/> "metadata":<br/>     {"CPU-demand": 42,<br/>      "privacy-zone": "zone-A",<br/>      "timeout": 42}</pre> | <pre>{"data": "Data42",<br/> "function": "FunctionData42",<br/> "metrics":<br/>     {"elapsed_time": 2,<br/>      "ret": 0},<br/> "uuid": "e09270d1-2760-4fba-b15a-255a9983ddd6"}</pre> |

#### Test cases with endpoints requestEdgeProc / requestPrivacyEdgeProc

| Test case | Test description                                                         | Prerequisites                                             | Inputs                                                                                 | Expected Outcome                                                       |
|-----------|--------------------------------------------------------------------------|-----------------------------------------------------------|----------------------------------------------------------------------------------------|------------------------------------------------------------------------|
| _#1_      | A TriggeringBB makes an invocation with a **valid** input JSON.          | The TriggeringBB obtained contract / function references. | Valid input JSON, e.g., example input                                                  | Deploy request **accepted**.                                           |  <!-- 202 -->
| _#2_      | A TriggeringBB makes an invocation with an **invalid** input JSON.       | The TriggeringBB obtained contract / function references. | Mandatory field(s) is missing, e.g., `<data_contract>`                                 | Deploy request **denied** due to _malformed request format_.           |  <!-- 400 -->  
| _#3_      | A TriggeringBB makes an invocation with an **unaccredited** input JSON.  | The TriggeringBB obtained contract / function references. | Forged / invalid contract_id / consent_id, e.g., `<func_contract>:=contract123-bogus`, | Deploy request **denied** due to _prohibited contract / consent_.      |  <!-- 403 -->
| _#4_      | A TriggeringBB makes an invocation with an **incomplete** input JSON.    | The TriggeringBB obtained contract / function references. | Forged / invalid data_id / func_id, e.g., `<func_id>:=null`,                           | Deploy request **denied** due to _missing execution parameter_.        |  <!-- 404 -->
| _#5_      | A TriggeringBB makes an invocation with an **unfulfillable** input JSON. | The TriggeringBB obtained contract / function references. | Impractical execution condition(s), e.g., `<timeout>:=0`,                              | Deployment process **failed** due to _deployment timeout_.             |  <!-- 408 -->
| _#6_      | A TriggeringBB makes an invocation with a **restrictive** input JSON.    | The TriggeringBB obtained contract / function references. | Unfeasible privacy restriction(s), e.g., `<pz_id>:="zone-B"`,                          | Deployment process **failed** due to _privacy zone restriction_.       |  <!-- 412 -->
| _#7_      | A TriggeringBB makes an invocation with an **excessive** input JSON.     | The TriggeringBB obtained contract / function references. | Unfulfillable compute demand(s), e.g., `<cpu>:=100`,                                   | Deployment process **failed** due to _insufficient compute resources_. |  <!-- 503 -->
