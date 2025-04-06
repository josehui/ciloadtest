# CI Load Test

This repository demonstrates a CI pipeline for load testing using GitHub Actions.

---

## Table of Contents

- [CI Load Test](#ci-load-test)
  - [Table of Contents](#table-of-contents)
  - [Introduction](#introduction)
  - [Features](#features)
  - [Folder Structure](#folder-structure)
  - [Prerequisites](#prerequisites)
  - [Local Testing](#local-testing)
  - [Some Design Decisions](#some-design-decisions)
  - [Potential Improvements](#potential-improvements)
  - [Time taken](#time-taken)

---

## Introduction

The project showcases how to automate load testing in a CI pipeline using Kubernetes and GitHub Actions. It deploys a sample HTTP application (`http-echo`) to a Kubernetes cluster, performs load testing using Vegeta, and monitors resource usage with the Kubernetes Metrics Server.

---

## Features

- **Kubernetes Setup**: Setup an ephemeral load test environment on Kubernetes with Kind, Helm
- **Kubernetes Deployment**: Deploys a sample HTTP application (`http-echo`) using Kustomize.
- **Load Testing**: Uses Vegeta to perform HTTP load testing with configurable parameters.
- **Resource Monitoring**: Tracks CPU and memory usage of pods during load testing.

---

## Folder Structure

The repository is organized as follows:

```
ciloadtest/
├── .github/
│   └── workflows/          # GitHub Actions workflows
│       └── main.yml        # CI pipeline definition
├── github-actions-lib/     # Custom GitHub Actions
│   ├── install-deps/       # Action to install local dependencies
│   ├── k8s-setup/          # Action to set up Kubernetes cluster
│   ├── k8s-deploy/         # Action to deploy Kubernetes resources
│   └── http-loadtest/      # Action to run HTTP load tests and monitor resources
├── ops/
│   └── k8s/                # Kubernetes manifests
│       ├── base/           # Base manifests for Kustomize
│       └── overlays/       # Overlays for different environments
├── README.md               # Project documentation
```

---

## Prerequisites

The workflow is designed to run on cloud hosted runners. Below dependencies are only required during local development

- [act](https://nektosact.com/installation/index.html) - For running github actions locally
- Docker
- Python3.10+
- Pre-commit

---

## Local Testing

To test the pipeline locally:

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/ciloadtest.git
   cd ciloadtest
   ```
2. Trigger ci-loadtest workflow
   ```bash
   act pull_request --rm
   ```
3. Cleanup kind cluster
   ```bash
   docker ps -a --filter "name=kind" -q | xargs -r docker stop
   docker ps -a --filter "name=kind" -q | xargs -r docker rm
   ```

---

## Some Design Decisions

1. **Kustomize for Deployment**: Kustomize is used for managing Kubernetes manifests, avoiding boilerplate and repetition of configuration.
2. **Vegeta for Load Testing**: Vegeta is chosen for its simplicity and flexibility in performing HTTP load tests with configurable parameters. The loadtest is executed from the host instead of within the cluster to simulate external traffic going through ingress.
3. **Metrics-server for Resource Monitoring**: metrics-server is chosen over Prometheus or other heavier solution to reduce load on runner and speed up setup.
4. **Imgur Integration**: Resource usage plots are uploaded to Imgur because I couldnt find how to upload an image to github from Github action.

---

## Potential Improvements

1. **Build from source**: Enable building from source instead of deploying an existing image
2. **Enhanced monitoring**: Integrate external Prometheus and Grafana for collecting and visualizing custom application metrics during load testing.
3. **Loadtest worker pool**: Support a pool of loadtest workers to run load tests in parallel and higher traffic load.
4. **Resource limit**: Enable resource limit for deployments.

---

## Time taken
5 hours, went into more rabbit holes than I expected.
