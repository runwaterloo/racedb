# Infrastructure Component Upgrade Procedure

This document describes the process for bumping core infrastructure dependencies (K3S, Helm, Traefik, Grafana Alloy) in this repository.

## 1. Pick New Versions

- K3S: [Latest release](https://github.com/k3s-io/k3s/releases/latest)
- Helm: [Latest release](https://github.com/helm/helm/releases/latest)
- Traefik: [Helm chart](https://artifacthub.io/packages/helm/traefik/traefik)
- Grafana Alloy: [Helm chart](https://artifacthub.io/packages/helm/grafana/alloy)

Review release notes as required.

## 2. Update Version Files

- Update `deploy/k3s/K3S_VERSION`
- Update `deploy/helm/HELM_VERSION`
- Update `deploy/traefik/TRAEFIK_CHART_VERSION`
- Update `deploy/alloy/ALLOY_CHART_VERSION`

## 3. Push a Branch

- Commit your changes to a new branch, prefix commit message with `chore(deps):`
- Exampe commit message:

```
chore(deps): upgrade infrastructure components (Jun 2025)

K3S: v1.32.3+k3s1 -> v1.33.1+k3s1
Helm: v3.17.3 -> v3.18.3
Traefik: 35.0.0 -> 36.2.0
Grafana Alloy: 1.0.3 -> 1.1.2
```

- Push the branch to GitHub

## 4. Create Pull Request

- Create a pull request
- Confirm all checks pass

## 4. Test the Upgrade at AWS

- Start a launch from template
- In Advanced details / user data, change the branch to yours
- Launch the instance
- Verify everything works as expected
- Delete the test instance

## 5. Merge and Deploy

- Merge your pull request
- Perform a "Redeploy RRW"

---

_Keep this document up to date as the process evolves._
