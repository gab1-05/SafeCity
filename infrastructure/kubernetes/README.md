# Kubernetes deployment (Helm only)

Deployment uses the Helm chart in `infrastructure/helm/safecity`. There are no Kustomize
overlays here, and that is a deliberate decision, not an omission:

- The chart already parameterizes every environment difference through values files
  (`values.yaml`, `values-dev.yaml`, `values-kind.yaml`, `values-staging.yaml`,
  `values-prod.yaml`) — which is exactly what overlays would otherwise duplicate.
- Kustomize's `helmCharts:` field cannot reference a chart by local path, so overlays over
  this chart would first require publishing it to a chart repository — extra machinery for
  no added capability at this project's scale.

## How it is exercised

- **CI** (`.github/workflows/k8s-validate.yml`): `helm lint` + `helm template` for the dev
  and kind values files, then `kubeconform -strict` over the rendered output.
- **Local (kind)**: `scripts/kind-deploy.sh` installs PostgreSQL/Redis (Bitnami charts),
  builds and loads the SafeCity images, then runs `helm upgrade --install` with
  `values-kind.yaml`.

## Manual verification

```bash
helm lint infrastructure/helm/safecity -f infrastructure/helm/safecity/values-kind.yaml
helm template safecity infrastructure/helm/safecity \
  -f infrastructure/helm/safecity/values-dev.yaml > /tmp/rendered.yaml
kubeconform -strict -ignore-missing-schemas /tmp/rendered.yaml
```

If overlays are ever needed (e.g. many divergent environments), add them here and wire them
into the `k8s-validate` workflow in the same change.
