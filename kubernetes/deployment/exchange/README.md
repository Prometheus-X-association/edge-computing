# Exchange setup for testing data exchange via Visions Catalog

## Prerequisite

```bash
$ make build
```

## Setup

```bash
$ make setup
```

To only initiate basic infrastructure components without provider/consumer APIs, use the dedicated target:

```bash
$ make setup-base
```

To initiate packet sniffers and examine PDC --> API invocations, use the following target:

```bash
$ make setup-all
```

To check component status, use the following target:

```bash
$ make status
```

## Testing

Copy the sample exchange config file and fill out the PDC / tunnel / contract secrets:

```bash
$ cp creds/exchange.env.sample creds/exchange.env 
```

Test exchange configuration can be given in `exchange.env` or in a separate env file
that is directly used by a `test_<...>.sh` script.

Execute test using Makefile targets or directly with helper scripts:

```bash
$ make test-config
$ make test-credential
$ make test-exchange
...
```

To see logs, use the target:

```bash
make logs
```

## Tearing down

```bash
$ make teardown
```