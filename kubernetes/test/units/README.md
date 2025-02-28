## Unit Testing

Unit tests are based on (Python) module tests separately defined under
`kubernetes/src/<module>/tests` for each `ptx-edge` subcomponent `<module>`.

### Setup Test Environment

For installing test dependencies of a given submodule in `kubernetes/src`,
use

```bash
$ cd kubernetes/src/<module> && make setup
# or
$ cd kubernetes/src/<module> && make docker-test-setup  # Preferred way
```

### Run Tests

To execute the unit tests of a single `<module>`, execute the dedicated
_Makefile target_ within the `<module>` folder, e.g.,

```bash
$ cd kubernetes/src/<module> && make unit-tests
# or
$ cd kubernetes/src/<module> && make docker-unit-tests  # Preferred way
```

To execute all unit tests defined for `ptx-edge`,
use the following helper script in `kubernetes/test/units`:

```bash
$ cd kubernetes/test/units && ./runall.sh
# or
$ cd kubernetes/test/units && ./runall.sh -d -o results # Preferred way

```

JUnit-style test reports are automatically generated and stored in the
test containers.
To export these reports from the test environment to the local host/VM,
use the `-o` flag with the `runall.sh` script.

For the available configuration parameters, refer to the help menu:

```bash
$ ./runall.sh -h
Usage: ./runall.sh [options]

Options:
    -d          Execute tests in Docker containers instead of local venvs.
    -o <dir>    Collect Junit-style reports into <dir>.
    -h          Display help.
```

### Expected Results

Each component test (script) starting with the prefix `test` is executed
successfully (without `error`/`failure` notification),
while the helper script `runall.sh` returns with value `0`.

Programmatically, each Makefile returns the value `0` in case all executed tests defined in the target
`unit-tests` were successful, and a non-zero value otherwise.
The helper script `runall.sh` follows this "UNIX" behavior as well.

### Test Execution Summary

> [!IMPORTANT]
>
> Since the _Edge computing - AI processing BB_ (`ptx-edge`) is still
> **under development**, the defined test cases only cover the implemented
> parts of `ptx-edge`'s planned capabilities.
> Further test cases are expected to be added continuously.

| Test Suite        | Test Case ID | Description | Expected Outcome | Actual Outcome | Status | Notes |
|-------------------|--------------|-------------|------------------|----------------|--------|-------|
| ptx-edge-builder  |              |             |                  |                |        |       |
| ptx-edge-rest-api |              |             |                  |                |        |       |

| Test Suite        |               Test Case ID               | Description                | Expected Outcome                                             |   Actual Outcome   | Status | Notes          |
|-------------------|:----------------------------------------:|----------------------------|--------------------------------------------------------------|:------------------:|:------:|----------------|
| ptx-edge-mock-api |   _test_live_server_is_up_and_running_   | Test server status         | [test-report-mock-api.xml](results/test-report-mock-api.xml) | :heavy_check_mark: |   OK   |                |
| ptx-edge-mock-api |      _test_request_edge_proc_a_ok_       | Test valid input           | [test-report-mock-api.xml](results/test-report-mock-api.xml) | :heavy_check_mark: |   OK   |                |
| ptx-edge-mock-api |     _test_request_edge_proc_fail400_     | Test invalid input         | [test-report-mock-api.xml](results/test-report-mock-api.xml) |        :x:         |   OK   | Assert failure |
| ptx-edge-mock-api |     _test_request_edge_proc_fail403_     | Test unaccredited request  | [test-report-mock-api.xml](results/test-report-mock-api.xml) |        :x:         |   OK   | Assert failure |
| ptx-edge-mock-api |     _test_request_edge_proc_fail404_     | Test incomplete request    | [test-report-mock-api.xml](results/test-report-mock-api.xml) |        :x:         |   OK   | Assert failure |
| ptx-edge-mock-api |     _test_request_edge_proc_fail408_     | Test unfulfillable request | [test-report-mock-api.xml](results/test-report-mock-api.xml) |        :x:         |   OK   | Assert failure |
| ptx-edge-mock-api |     _test_request_edge_proc_fail412_     | Test restrictive request   | [test-report-mock-api.xml](results/test-report-mock-api.xml) |        :x:         |   OK   | Assert failure |
| ptx-edge-mock-api |     _test_request_edge_proc_fail503_     | Test oversize request      | [test-report-mock-api.xml](results/test-report-mock-api.xml) |        :x:         |   OK   | Assert failure |
| ptx-edge-mock-api |  _test_request_privacy_edge_proc_a_ok_   | Test valid input           | [test-report-mock-api.xml](results/test-report-mock-api.xml) | :heavy_check_mark: |   OK   |                |
| ptx-edge-mock-api | _test_request_privacy_edge_proc_fail400_ | Test invalid input         | [test-report-mock-api.xml](results/test-report-mock-api.xml) |        :x:         |   OK   | Assert failure |
| ptx-edge-mock-api | _test_request_privacy_edge_proc_fail401_ | Test unauthorized request  | [test-report-mock-api.xml](results/test-report-mock-api.xml) |        :x:         |   OK   | Assert failure |
| ptx-edge-mock-api | _test_request_privacy_edge_proc_fail403_ | Test unaccredited request  | [test-report-mock-api.xml](results/test-report-mock-api.xml) |        :x:         |   OK   | Assert failure |
| ptx-edge-mock-api | _test_request_privacy_edge_proc_fail404_ | Test incomplete request    | [test-report-mock-api.xml](results/test-report-mock-api.xml) |        :x:         |   OK   | Assert failure |
| ptx-edge-mock-api | _test_request_privacy_edge_proc_fail408_ | Test unfulfillable request | [test-report-mock-api.xml](results/test-report-mock-api.xml) |        :x:         |   OK   | Assert failure |
| ptx-edge-mock-api | _test_request_privacy_edge_proc_fail412_ | Test restrictive request   | [test-report-mock-api.xml](results/test-report-mock-api.xml) |        :x:         |   OK   | Assert failure |
| ptx-edge-mock-api | _test_request_privacy_edge_proc_fail503_ | Test oversize request      | [test-report-mock-api.xml](results/test-report-mock-api.xml) |        :x:         |   OK   | Assert failure |
| ptx-edge-mock-api |     _test_get_versions_versions_get_     | Test version/heartbeat     | [test-report-mock-api.xml](results/test-report-mock-api.xml) | :heavy_check_mark: |   OK   |                |