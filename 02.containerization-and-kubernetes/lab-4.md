# Lab: Managing Kubernetes Workloads

## Context

In Kubernetes, applications run in Pods, which are ephemeral resources. A Pod can be deleted, restarted, or moved at any time. Kubernetes therefore introduces Workloads, higher-level objects that automatically create, monitor, and replace Pods to maintain the desired state of the application. They eliminate the need to manage each Pod individually. Each type of Workload addresses a specific need.

- ReplicaSet: maintains the defined number of running Pod replicas. It is used to increase or decrease the number of pods based on the traffic load that when it is heavy, it needs to be distributed across multiple Pods.
- Deployment: is a higher-level object that manages a ReplicaSet to keep a desired number of identical Pods running. Unlike a ReplicaSet, it is designed to handle updates to Pods declaratively, enabling rolling updates and rollbacks. It is used for stateless applications that do not require persistent storage or stable Pod identity.
- StatefulSet: manages Pods whose are not interchangeable and require stable identities. It is suitable for stateful applications, when the application needs persistance storage.
- DaemonSet: ensures that one Pod runs on every node, or on a selected subset of nodes. It is suitable when deploying node-level services.
- Job and CronJob: execute tasks until they are completed and stopped. Pods are created to run the tasks and are terminated once the tasks are finished. A Job is used for a specific one-time task, while a CronJob is used for a recurring task that must run according to a defined schedule. These Workloads will not be covered in this lab.

> Note: the DaemonSet, Job and CronJob will not be covered in this lab.

## Objectives

- Create a ReplicaSet
- Update a Deployment (rollout and rollback)
- Deploy a StatefulSet with persistent storage

## Prerequisites

- A running Kubernetes cluster (minikube)
- Familiarity with Pods and basic `kubectl` commands
- Previous labs completed

## Setup

```bash
kubectl create namespace k8s-lab-workload
```

> **Note:** all resources of this lab live in the `k8s-lab-workload` namespace. Add `-n k8s-lab-workload` to every `kubectl` command (or to your manifests' `metadata.namespace`).

> **Question 0.** You have already created Pods directly. What limits do you see with this approach for a production application? List at least two.

---

## Part 1: ReplicaSet

A ReplicaSet maintains a defined number of identical Pod replicas.

1. Create a ReplicaSet named `replicaset-frontend`: 3 replicas, image `nginx:1.29`, label `app=replicaset-frontend`. Use `kubectl explain replicaset.spec` or the [official documentation](https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/).
2. Check the result: `kubectl get rs` and `kubectl get pods --show-labels`.
3. Delete one of the Pods, then immediately list the Pods again.
4. Scale the ReplicaSet down to 2 replicas with `kubectl scale`.

> **Question 1.1.** After deleting a Pod, does the new Pod have the same name? What does this tell you about the identity of Pods managed by a ReplicaSet?
>
> **Question 1.2.** How does the ReplicaSet know which Pods belong to it? Test it: what happens if you change the label of an existing Pod with `kubectl label pod <pod> app=other --overwrite`?
>
> **Question 1.3.** Why is a ReplicaSet rarely used directly? An important feature is missing: which one? (Hint: Part 2.)

---

## Part 2: Deployment

A Deployment manages a ReplicaSet and adds declarative updates and rollbacks. It suits **stateless** applications.

### 2.1 Starting point

You already created a Deployment in the previous lab. Either reuse it, or create a new one inspired by it with these characteristics:

- name `deployment-web-app`, 2 replicas
- image `nginx:1.29`, label `app=deployment-web`

Wait for the deployment to complete with `kubectl rollout status`, then look at the ReplicaSet and Pods it created (`get deploy`, `get rs`, `get pods --show-labels`).

> **Question 2.1.** Decode the name of a Pod, for example `deployment-web-app-5cfc558677-jv99x`. What does each segment represent? Which additional label do the Pods carry, and what is it used for?

### 2.2 Update and rollback

1. Change the image to `nginx:1.29-alpine` with `kubectl set image`.
2. Observe the rollout, then run `kubectl get rs`, `kubectl describe deployment` and `kubectl rollout history`.
3. Display the details of revision 1 (`--revision=1`).
4. Go back to the previous version with `kubectl rollout undo`, then observe the ReplicaSets again.

> **Question 2.2.** After the update, has the old ReplicaSet disappeared? What does it contain (DESIRED/CURRENT)? Why does Kubernetes keep it?
>
> **Question 2.3.** Which changes to the manifest trigger a new rollout? Verify experimentally: does changing the number of replicas create a new revision?
>
> **Question 2.4.** In `describe deployment`, find the update strategy (`StrategyType`, `RollingUpdateStrategy`). What do `maxSurge` and `maxUnavailable` mean? What would happen with the `Recreate` strategy?

### 2.3 Scaling and autoscaling

1. Scale the Deployment to 5 replicas.
2. Create a HorizontalPodAutoscaler (`kubectl autoscale`): min 2, max 10, CPU target 75%.
3. Display the HPA: `kubectl get hpa`.

> **Question 2.5.** The `TARGETS` column shows `<unknown>/75%`. Find **two possible causes** and fix them. (Hints: `minikube addons`, and `resources.requests` in the Pod.)
>
> **Question 2.6.** After creating the HPA, how many replicas does the Deployment have after one minute? Why?

---

## Part 3: StatefulSet and Headless Service

A StatefulSet manages **non-interchangeable** Pods: stable identity (name, network) and persistent storage specific to each Pod. It suits databases, message brokers and distributed storage. 

A [Headless Service](https://kubernetes.io/docs/concepts/services-networking/service/#headless-services) provides to each Pod a stable network identity. This is necessary when each Pod in a set of Pods has a specific role, as is the case in a database cluster where one acts as the master and the others as replicas. The Service is first created and then associated with the StatefulSet.

### 3.1 Creation

Create a **Headless Service** `statefulset-svc` (`clusterIP: None`, selector `app=statefulset-pod`), then a **StatefulSet** `statefulset-workload`:

- 3 replicas, image `busybox:1.36`, command `sleep infinity`
- `serviceName` pointing to the headless Service
- a `volumeClaimTemplates` entry named `data` (100Mi, `ReadWriteOnce`) mounted on `/data`

Check: `get statefulset`, `get pods`, `get svc`, `get pvc`.

> **Question 3.1.** Is the `serviceName` field mandatory? Try creating the StatefulSet without it and read the error.
>
> **Question 3.2.** Compare the Pod names with those of a Deployment. How are they named? In which order are they created (`kubectl get pods -w` while recreating the StatefulSet)?
>
> **Question 3.3.** How many PVCs were created? How are they named? What distinguishes them from a single PVC shared by all Pods?

### 3.2 Persistence

1. In Pod `statefulset-workload-1`, write a file in `/data` containing the hostname.

```bash
kubectl -n k8s-lab-workload exec \
  <pod-name> -- \
  sh -c 'echo "Hello from $(hostname)" > /data/test_statefulset.txt'
```

Verify that file is created in the Pod.

2. Delete this Pod, wait for it to be recreated, and read the file again.

> **Question 3.4.** Does the file still exist? What happens if you delete a Pod of the Deployment from Part 2: do its local data survive?
>
> **Question 3.5.** Delete the StatefulSet (`kubectl delete statefulset statefulset-workload`), then list the PVCs. What do you observe? What is the impact on data management?

---

## Teardown

Created resources are removed.

```bash
kubectl delete ns k8s-lab-workload
```
