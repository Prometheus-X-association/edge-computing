## Component-Level Testing

Testing of `ptx-edge` components is based on the basic functionality
and applicability of `ptx-edge` K8s components.

### Setup Test Environment

```bash
$ ./install-dep.sh -u
```

### Run Tests

```bash
$ ./runall.sh -o ./results
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

Each component test script starting with the prefix `test` in the folder
`kubernetes/test/suites` is executed successfully (without `error`/`failure` notification),
while the helper script `runall.sh` returns with value `0`.

Programmatically, each test script returns `0` in case all defined test
cases were successful, and a non-zero value otherwise.\
The helper script `runall.sh` follows this UNIX behavior as well.

### Test Execution Summary

> [!IMPORTANT]
>
> Since the _Edge computing - AI processing BB_ (`ptx-edge`) is still
> **under development**, the defined test cases only cover the implemented
> parts of `ptx-edge`'s planned capabilities.
> Further test cases are expected to be added continuously.

| Test Suite             |                Test Case ID                | Description                       | Expected Outcome                                                                         |   Actual Outcome   | Status  | Notes                                                |
|------------------------|:------------------------------------------:|-----------------------------------|------------------------------------------------------------------------------------------|:------------------:|:-------:|------------------------------------------------------|
| near-data-scheduling   |  _testNearDataSchedulingWithNodeAffinity_  | Test K8s node affinity/preference | [test-report-near-data-scheduling.xml](results/test-report-near-data-scheduling.xml)     | :heavy_check_mark: |   OK    |                                                      |
| pod-scheduling         |     _testSchedulingWithCPUConstraint_      | Test K8s pod cpu limits           | [test-report-pod-scheduling.xml](results/test-report-pod-scheduling.xml)                 | :x: |   OK    | Assert failure                                       |
| pod-scheduling         |    _testSchedulingWithMemoryConstraint_    | Test K8s pod memory limits        | [test-report-pod-scheduling.xml](results/test-report-pod-scheduling.xml)                 | :x: |   OK    | Assert failure                                       |
| policy-zone-scheduling | _testPolicyZoneSchedulingWithNodeSelector_ | Test K8s node selector            | [test-report-policy-zone-scheduling.xml](results/test-report-policy-zone-scheduling.xml) | :heavy_check_mark: |   OK    |                                                      |
| policy-zone-scheduling | _testPolicyZoneSchedulingWithNodeAffinity_ | Test K8s node affinity            | [test-report-policy-zone-scheduling.xml](results/test-report-policy-zone-scheduling.xml) | :heavy_check_mark: |   OK    |                                                      |
| ptx-edge-builder       |       _testPTXEdgeStaticVolumeClaim_       | Test K8s local volume             | [test-report-ptx-edge-builder.xml](results/test-report-ptx-edge-builder.xml)             | :heavy_check_mark: | SKIPPED | Static volumes not supported in **K3s** `local-path` |
| ptx-edge-builder       |      _testPTXEdgeDynamicVolumeClaim_       | Test K3s local-path volume        | [test-report-ptx-edge-builder.xml](results/test-report-ptx-edge-builder.xml)             | :heavy_check_mark: |   OK    |                                                      |
| ptx-edge-builder       |            _testPTXEdgeBuilder_            | Test `builder` config             | [test-report-ptx-edge-builder.xml](results/test-report-ptx-edge-builder.xml)             | :heavy_check_mark: |   OK    |                                                      |
| ptx-edge-rest-api      |            _testPTXEdgeRESTAPI_            | Test `rest-api` config            | [test-report-ptx-edge-rest-api.xml](results/test-report-ptx-edge-rest-api.xml)           | :heavy_check_mark: |   OK    |                                                      |
| ptx-connector          |          _testPTXSandboxCatalog_           | Test ptx-core sandbox config      | [test-report-ptx-connector.xml](results/test-report-ptx-connector.xml)                   | :heavy_check_mark: |   OK    |                                                      |
| ptx-connector          |          _testPTXConnectorConfig_          | Test `pdc` config                 | [test-report-ptx-connector.xml](results/test-report-ptx-connector.xml)                   | :heavy_check_mark: |   OK    |                                                      |
| ptx-connector          |             _testPTXConnector_             | Test `pdc` deployment             | [test-report-ptx-connector.xml](results/test-report-ptx-connector.xml)                   | :heavy_check_mark: |   OK    |                                                      |
