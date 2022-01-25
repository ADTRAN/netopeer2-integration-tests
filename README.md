# Netopeer2 Integration Tests

[![Build Status](https://travis-ci.org/ADTRAN/netopeer2-integration-tests.svg?branch=master)](https://travis-ci.org/ADTRAN/netopeer2-integration-tests)

This repository contains several tests that run against the Netopeer2
NETCONF server. The goal is to test the entire stack of software all
running together, as it would in a real deployment.

## System requirements
 - make
 - docker
 - git

## Running the tests

If you run `make test` the build system will setup its environment and
run the pytest tests.

If you don't have a populated `repo` directory already, the latest dev
versions of the Netopeer2 stack will be cloned. If you already have a
populated `repo` directory it will remain unchanged.

There are long running tests which will not run without extra options.
Use `make test PYTEST_ARGS='-m long_runner'` to execute them.

## Directories

### `tests`

This directory contains all of the tests and supporting Python code
for implementing the tests.

The `make format` target will clean up the formatting of the Python
code in this directory.

### `yang`

This directory contains all of the YANG models that will be installed
for use in the tests. `yang/manifest.json` can be used to control what
files are installed and which features are enabled.

### `test-service`

This directory contains the implementation for a test service, which
captures information from the south-bound API of sysrepo so that tests
can verify events are emitted under certain stimuli.

### `support`

This directory contains various supporting files (scripts and
configuration) to help launch the Netopeer2 stack.

### `patch`

This directory may contain patches to be applied to the source repositories
in directory `repo` before they are built. A patch can be generated this way:
```
rm -rf repo
make test-env
# edit the source files in repo/{REPONAME}/src
git diff >patch/{REPONAME}
```
The placholder {REPONAME} stands for the name of one of the source repositories
libnetconf2, libyang, Netopeer2 or sysrepo.

In order to apply the patches and to build the patched repositories use:
```
rm -rf repo
make test-env
```
