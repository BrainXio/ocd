---
name: kubernetes
description: Write, audit, and debug Kubernetes manifests, Helm charts, and kubectl workflows. Use when creating, reviewing, or fixing Kubernetes YAML, Helm templates, Kustomize overlays, or cluster operations.
argument-hint: "[manifest path or 'audit' or 'debug']"
title: "Kubernetes Skill Reference"
aliases: ["kubernetes-skill"]
tags: ["skill", "tool", "kubernetes"]
created: "2026-04-24"
updated: "2026-04-24"
---

# Kubernetes Skill

You are a Kubernetes expert who writes secure, declarative, production-grade manifests following these conventions.

## Mandatory Rules

- Every workload must have `resources.requests` and `resources.limits` set — no unbounded pods
- Every workload must have `livenessProbe` and `readinessProbe` — no blind traffic routing
- Every Pod template must have `securityContext` with `runAsNonRoot: true` and `readOnlyRootFilesystem: true`
- Never use `latest` tag for container images — always pin to a specific digest or version tag

## Critical Rules

### Security

- Set `runAsNonRoot: true` — never run as root
- Set `readOnlyRootFilesystem: true` — use `emptyDir` volumes for writable paths
- Drop all capabilities: `capabilities: { drop: ["ALL"] }`
- Set `allowPrivilegeEscalation: false`
- Use `NetworkPolicy` to restrict pod-to-pod traffic — default deny ingress
- Use `SealedSecrets` or external secret managers (Vault, AWS Secrets Manager) — never plaintext `Secret` manifests
- Use `ServiceAccount` with minimal RBAC — never `cluster-admin` unless absolutely necessary
- Never mount `docker.sock` or the node filesystem into pods
- Use `PodSecurityStandard: restricted` profile via `PodSecurity` admission

### Resource Management

- Always set both `requests` and `limits` for CPU and memory
- Set `requests` to actual usage (P99 is a good baseline), `limits` to allow brief spikes
- Use `LimitRange` to set defaults and prevent zero-resource deployments
- Use `ResourceQuota` to cap namespace-level consumption
- Use `HorizontalPodAutoscaler` for workloads with variable load — set `minReplicas >= 2`

### Reliability

- Set `replicas >= 2` for production workloads — single points of failure are unacceptable
- Use `PodDisruptionBudget` with `minAvailable` or `maxUnavailable` for rolling updates
- Set `topologySpreadConstraints` to distribute across zones — never rely on default scheduling
- Use `inter-pod anti-affinity` to spread replicas across nodes
- Set appropriate `revisionHistoryLimit` (default 10 is fine, reduce for high-churn deployments)
- Always use `RollingUpdate` strategy with explicit `maxSurge` and `maxUnavailable`

### Labels and Annotations

- Every resource must have standard labels:
  ```yaml
  labels:
    app.kubernetes.io/name: <name>
    app.kubernetes.io/instance: <release>
    app.kubernetes.io/version: <version>
    app.kubernetes.io/component: <role>
    app.kubernetes.io/part-of: <system>
    app.kubernetes.io/managed-by: <tool>
  ```
- Never use bare `app: <name>` as the only label
- Use `matchLabels` in selectors — never `matchExpressions` for simple equality

### Configuration

- Use `ConfigMap` for non-sensitive config — `Secret` for sensitive data (base64-encoded)
- Mount configs as volumes rather than env vars for large or structured data
- Use `envFrom` with `configMapRef` / `secretRef` for bulk injection
- Reference individual keys with `valueFrom` for explicit, traceable binding
- Never hardcode environment-specific values in manifests — use Kustomize overlays or Helm values

### Networking

- Use `Service` with explicit `type` — never rely on default (`ClusterIP`)
- Use `Ingress` with TLS — never expose HTTP for production
- Use `NetworkPolicy` to enforce least-privilege pod communication
- Prefer `headless Services` for StatefulSet internal communication
- Use `topologyAwareHints` for zone-aware routing where supported

## Manifest Structure

Standard deployment manifest skeleton:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
  labels:
    app.kubernetes.io/name: app
    app.kubernetes.io/part-of: system
spec:
  replicas: 2
  selector:
    matchLabels:
      app.kubernetes.io/name: app
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app.kubernetes.io/name: app
    spec:
      securityContext:
        runAsNonRoot: true
        readOnlyRootFilesystem: true
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: app
          image: registry/app:1.0.0
          ports:
            - containerPort: 8080
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 256Mi
          livenessProbe:
            httpGet:
              path: /healthz
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: 8080
            initialDelaySeconds: 3
            periodSeconds: 5
          volumeMounts:
            - name: tmp
              mountPath: /tmp
      volumes:
        - name: tmp
          emptyDir: {}
```

## Helm Conventions

When writing Helm charts:

- Use `values.yaml` with sensible defaults and documented comments
- Never put secrets in `values.yaml` — reference external secret stores
- Use `{{ include }}` over inline templates for shared snippet reuse
- Use `_helpers.tpl` for common labels and names
- Use `.Values.*` references — never hardcode in templates
- Set `app.kubernetes.io/version: {{ .Chart.AppVersion }}` from `Chart.yaml`
- Use `required` function for mandatory values: `{{ required "A valid .Values.image.repository is required" .Values.image.repository }}`
- Scope hooks with `helm.sh/hook-weight` annotations

## Kustomize Conventions

When writing Kustomize overlays:

- `base/` for common resources, `overlays/<env>/` for environment-specific patches
- Use `patchesStrategicMerge` for simple overrides, `patchesJson6902` for precise JSON patch
- Use `configMapGenerator` and `secretGenerator` — never static ConfigMaps in overlays
- Use `commonLabels` and `commonAnnotations` sparingly — they taint selectors
- Use `namespace` transformer to set namespace — never hardcode in resources

## Validation

```bash
# Validate manifests
kubectl apply --dry-run=client -f manifest.yaml

# Validate with kubeval/kubeconform
kubeconform -summary manifest.yaml

# Lint Helm charts
helm lint chart/
helm template chart/ | kubeconform -

# Diff before apply
kubectl diff -f manifest.yaml

# Check rollout status
kubectl rollout status deployment/app --timeout=120s
```

## Anti-Patterns to Avoid

- `image: latest` — always pin to a specific tag or digest
- Running as root — always `runAsNonRoot: true`
- Missing `resources` — unbounded pods destabilize the node
- Missing probes — kubelet can't detect dead or unready pods
- `hostPath` volumes — use `PersistentVolumeClaim` or `emptyDir`
- `hostNetwork: true` — use `Service` instead
- `privileged: true` — never, redesign the workload
- Bare `Secret` manifests in git — use sealed-secrets or external operators
- `cluster-admin` ClusterRoleBinding — use least-privilege RBAC
- Tiller (Helm 2) — use Helm 3 only, no server-side components
- `namespace: default` for production workloads — always use dedicated namespaces
- Overlapping selectors across Deployments managing the same Pods
