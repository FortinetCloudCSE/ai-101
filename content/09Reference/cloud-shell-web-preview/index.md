---
title: "Troubleshooting Azure Cloud Shell Web Preview"
linkTitle: "Cloud Shell Web Preview"
hidden: true
weight: 10
deploymentPath: k8s
---

{{% notice style="note" title="Kubernetes / Helm path only" %}}
This page applies to the **Kubernetes / Helm** path only. On the **Docker Compose**
path the UI is published on your own machine at `http://localhost:8080` and Azure
Cloud Shell is not involved.
{{% /notice %}}

Azure Cloud Shell Web Preview uses an authenticated Azure proxy to expose a
port from your Cloud Shell session. An **Unauthorized** response can therefore
come from the browser-to-Azure connection even when the Kubernetes service and
the `kubectl port-forward` are healthy.

## Confirm the UI is reachable from Cloud Shell

Run this command in the same Cloud Shell session you use to open Web Preview:

```bash
curl -sS -o /dev/null -w 'HTTP %{http_code}\n' http://127.0.0.1:8100/
```

If it returns `HTTP 200`, the UI and port-forward are working. Continue with
the browser-specific steps below.

If it does not return `HTTP 200`, start the port-forward and try the check
again:

```bash
kubectl port-forward svc/ai101-ui 8100:80 > /tmp/ai101-ui-port-forward.log 2>&1 < /dev/null &
```

The port-forward runs in the background. Connection messages are written to
`/tmp/ai101-ui-port-forward.log` instead of interrupting your terminal.

## Firefox

1. On the preview page that displays **Unauthorized**, click the shield icon
   beside the address bar.
2. Turn off **Enhanced Tracking Protection** for that site.
3. Repeat this for the tab hosting `portal.azure.com` or `shell.azure.com`.
4. Reload Cloud Shell, then reopen Web Preview on port **8100**.

Use a regular Firefox window rather than a Private Window. If you use Firefox
Multi-Account Containers, open Cloud Shell and Web Preview in the same
container so they share the Azure authentication session.

See Mozilla's documentation for
[enabling cross-site cookies for a specific site](https://support.mozilla.org/en-US/kb/third-party-cookies-firefox-tracking-protection).

## Chrome

1. Open **Settings** → **Privacy and security** → **Third-party cookies**.
2. Under **Sites allowed to use third-party cookies**, select **Add**.
3. Add `[*.]console.azure.com`.
4. Reload Cloud Shell, then reopen Web Preview on port **8100**.

Use a regular browser window rather than Incognito. See Google's documentation
for [allowing third-party cookies for a specific site](https://support.google.com/chrome/answer/95647).

## Microsoft Edge

1. Open **Settings** → **Privacy, search, and services** → **Cookies**.
2. Allow sites to save and read cookie data, and add
   `[*.]console.azure.com` to the allowed sites.
3. If Tracking prevention is set to **Strict**, temporarily change it to
   **Balanced**.
4. Reload Cloud Shell, then reopen Web Preview on port **8100**.

Use a regular browser window rather than InPrivate. See Microsoft's
documentation for [managing cookies in Edge](https://support.microsoft.com/en-us/edge/manage-cookies-in-microsoft-edge-view-allow-block-delete-and-use).

## If Web Preview is still Unauthorized

Run the port-forward and open Web Preview from the same Cloud Shell session.
You can also try a different local port to avoid stale preview state:

```bash
kubectl port-forward svc/ai101-ui 8101:80 > /tmp/ai101-ui-port-forward-8101.log 2>&1 < /dev/null &
```

Then confirm `http://127.0.0.1:8101/` returns `HTTP 200` and configure Web
Preview for port **8101**.

On a managed corporate network, ask your administrator to allow HTTPS and
WebSocket access to:

```text
*.console.azure.com
*.servicebus.windows.net
```

These domains are listed in Microsoft's
[Azure Cloud Shell troubleshooting guidance](https://learn.microsoft.com/en-us/azure/cloud-shell/faq-troubleshooting).
