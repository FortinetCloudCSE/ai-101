---
title: "Kubernetes / Helm Setup"
linkTitle: "Kubernetes / Helm"
weight: 2
---

## Prerequisites

| Requirement | Version | Check |
|-------------|---------|-------|
| kubectl | 1.28+ | `kubectl version --client` |
| Helm | 3.14+ | `helm version` |
| jq | 1.6+ | `jq --version` |
| A running cluster | — | `kubectl cluster-info` |
| Default StorageClass | — | `kubectl get storageclass` |

The Helm chart creates a PersistentVolumeClaim for Ollama's model cache. A
default StorageClass is required unless you set `ollama.storage.storageClassName`
explicitly.

If your cluster has no default StorageClass (check with `kubectl get storageclass`),
install [Rancher local-path-provisioner](https://github.com/rancher/local-path-provisioner) — it uses local node disk and works on any cluster:

```bash
kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/master/deploy/local-path-storage.yaml
kubectl patch storageclass local-path -p '{"metadata":{"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```

{{% notice style="warning" title="Resource requirements" %}}
Ollama needs at least 4 GB RAM on the node where it schedules. If your cluster
nodes are smaller, set the `OLLAMA_MODEL` env var to a lighter model in
`values-lab1.yaml`.
{{% /notice %}}

## 1. Clone the repo

```bash
git clone https://github.com/FortinetCloudCSE/ai-101.git
cd ai-101
```

## 2. Install the chart for Lab 1

Pre-built multi-arch images (amd64 + arm64) are published to GHCR and pulled
automatically by the cluster — no manual image pull required.

```bash
cd lab-app/helm
helm upgrade --install ai101 ./ai101 -f ai101/values-lab1.yaml
```

Wait for the Ollama pod to start, then follow its logs to track the model download:
```bash
kubectl get pods -w
```

Once the `ai101-ollama-*` pod shows `Running` (may take 60–90 s for the image pull), open a new terminal and follow the logs:
```bash
kubectl logs -l app.kubernetes.io/component=ollama -f
```

## 3. Verify

First, port-forward the Ollama service in a separate terminal (or background it with `&`):
```bash
kubectl port-forward svc/ai101-ollama 11434:11434 &
```

Then, in a new terminal, test inference:
```bash
curl -s http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5:3b","messages":[{"role":"user","content":"ping"}]}' \
  | jq -r '.choices[0].message.content'
```

## 4. Reference — upgrade per lab

```bash
cd lab-app/helm

# Lab 1 — Ollama only
helm upgrade --install ai101 ./ai101 -f ai101/values-lab1.yaml

# Lab 2 — Agent (hardcoded tools) + UI
helm upgrade --install ai101 ./ai101 -f ai101/values-lab2.yaml

# Lab 3 — Agent (MCP mode) + MCP server + UI
helm upgrade --install ai101 ./ai101 -f ai101/values-lab3.yaml

# Lab 4 — Same as lab3 (security demo steps use env overrides)
helm upgrade --install ai101 ./ai101 -f ai101/values-lab4.yaml
```

Access the UI (Lab 2 and later only — the UI is not deployed in Lab 1):
```bash
kubectl port-forward svc/ai101-ui 8100:80 &
```

Then open [http://localhost:8100](http://localhost:8100) in a browser.

**Azure Cloud Shell users** — `localhost` is not reachable from your browser. Use Web Preview instead:
click the **Web Preview** icon (top-right toolbar) → **Configure** → port **8100** → **Open and browse**.

{{% notice style="tip" title="Keep it running" %}}
Leave the release running as you work through the labs. Each lab section tells you which values file to upgrade to. Only uninstall when you are completely done.
{{% /notice %}}

---

The two sections below are **not part of the lab flow** — they are reference material for optional extensions and post-workshop teardown.

## 5. Optional — FortiAIGate routing

To route the agent through FortiAIGate instead of the local Ollama:

```bash
helm upgrade ai101 ./ai101 -f ai101/values-lab4.yaml \
    --set agent.openaiBaseUrl=https://your-fortiaigate-host/v1
```

See the [FortiAIGate Workshop](https://fortinetcloudcse.github.io/faig-training-workshop/)
for policy configuration details.

## 6. Cleanup (after the workshop)

```bash
helm uninstall ai101
kubectl delete pvc ai101-ollama-data
```
