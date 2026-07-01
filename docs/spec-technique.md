# Spec technique — platform-gitops

## Structure du dépôt

```
argocd/
  apps.yaml                    Métadonnées globales (domaine, registry, repoURL GitOps)
  apps/                        Descriptions applicatives ajoutées après bootstrap
  generated/apps/              Manifests ArgoCD générés après onboarding app
  managed/                     GÉNÉRÉ — ne pas éditer à la main
    apps-appset.yaml           ApplicationSet générique vers argocd/generated/apps/*
    gitlab.yaml                Application ArgoCD pour GitLab (chart Helm)
    platform-appset.yaml       ApplicationSet pour les composants plateforme
    terraform-gitlab.yaml      Application ArgoCD pour le contrôleur Terraform GitLab
  platform/                    Manifests des composants plateforme
    argocd-config/             Kustomization : argocd-cm, argocd-rbac-cm, argocd-cmd-params-cm
    argocd-ui/                 HTTPRoutes ArgoCD et Dex
    gitlab-routes/             HTTPRoutes GitLab
    gitlab-minio-patch/        Patch Kustomize Minio
    registry/                  Déploiement registry:2 + Service + HTTPRoute
docs/
  prd.md
  spec-fonctionnelle.md
  spec-technique.md
flux-secrets/
  github-credentials.yaml     Secret Flux chiffré SOPS pour lire GitHub
```

## `argocd/apps.yaml` — métadonnées plateforme

Ce fichier fixe les constantes résolues par `platform_inventory.py` :

```yaml
platform:
  domain: 192.168.33.100.nip.io
  repoURL: https://github.com/poc-devops-elkouhen/platform-gitops
  targetRevision: main
  registry:
    host: registry.registry.svc.cluster.local:5000

gitlab:
  internalHost: gitlab-webservice-default.gitlab.svc.cluster.local:8181

appsDir: apps
```

`repoURL` est l'URL externe (GitHub) utilisée pour le bootstrapping initial
d'ArgoCD. Une fois GitLab opérationnel, ArgoCD peut être reconfiguré pour
pointer vers l'instance GitLab interne.

Malgré son nom historique, ce fichier ne doit pas devenir un inventaire
applicatif détaillé. Les ressources d'une application doivent être décrites dans
`argocd/apps/<app>/app.yaml`.

## Secrets GitOps (`flux-secrets/`)

Les secrets applicatifs nécessaires aux contrôleurs GitOps sont versionnés sous
forme chiffrée avec SOPS/age dans `flux-secrets/`.

| Secret Kubernetes | Fichier | Consommateur |
|-------------------|---------|--------------|
| `github-credentials` | `flux-secrets/github-credentials.yaml` | `GitRepository/gitlab-projects-iac` et `Terraform/gitlab-iac` |

Flux applique ces secrets via `argocd/platform/tf-controller/flux-secrets-kustomization.yaml`
avec `decryption.provider: sops` et `secretRef.name: sops-age`. Le secret
`sops-age` reste un prérequis de bootstrap : il contient la clé privée age et ne
doit pas être committé.

Le secret `gitlab-tf-credentials` n'est pas versionné : `platform-cicd` le crée
après `gitlab-wait` via `make gitlab-tf-credentials`. Cette étape lit le mot de
passe root initial GitLab, crée/rotate un PAT `terraform-controller`, puis écrit
le Secret Kubernetes dans `flux-system` pour `Terraform/gitlab-iac`.

## `argocd/managed/` — point d'entrée généré

`argocd/managed/` contient les objets ArgoCD que l'Application racine applique
pour amorcer la plateforme : GitLab, Flux/tofu-controller, CRDs Terraform et
ApplicationSet des composants plateforme. Il contient aussi l'ApplicationSet
générique `apps-appset.yaml`, qui découvre les dossiers
`argocd/generated/apps/*` et crée une Application ArgoCD par dossier généré.

Ce répertoire n'est pas une couche métier distincte de `argocd/platform/` :
- `argocd/platform/` contient les manifests sources des composants plateforme ;
- `argocd/managed/` contient les Applications ArgoCD générées qui pointent vers
  ces manifests.

Il ne doit pas contenir d'`AppProject`, `Application`, `ApplicationSet`,
credential ou namespace propre à une application. Ces objets doivent être dans
`argocd/generated/apps/<app>/` et générés depuis `argocd/apps/<app>/app.yaml`.

## `argocd/apps/<app>/app.yaml` — description applicative

Le dépôt est livré sans application déclarée pour que le provisioning plateforme
reste indépendant. Après provisioning, chaque application possède une
description source :

| Fichier | Rôle |
|---------|------|
| `argocd/apps/<app>/app.yaml` | Nom, modules/services, dépôt code et dépôt IaC |
| `argocd/generated/apps/<app>/app-project.yaml` | Périmètre ArgoCD autorisé, généré |
| `argocd/generated/apps/<app>/applicationset.yaml` | Applications ArgoCD par environnement, générées |
| `argocd/generated/apps/<app>/repo-creds.yaml` | Secret ArgoCD/RBAC dédiés au dépôt manifests de l'app, générés |
| `argocd/generated/apps/<app>/kustomization.yaml` | Agrège les ressources générées |

La génération est lancée depuis `platform-cicd` :

```bash
make argocd-apps-render
make check-generated
```

## Configuration ArgoCD (`argocd/platform/argocd-config/`)

- **`argocd-cm.yaml`** : configure Dex avec le provider GitLab OIDC.
  Les valeurs `dex.gitlab.clientID` et `dex.gitlab.clientSecret` sont
  injectées dans `argocd-secret` par `gitlab-dex-oauth-app.py` lors du bootstrap.
- **`argocd-rbac-cm.yaml`** : mappe les groupes GitLab sur les rôles ArgoCD
  (`role:admin` pour tous les utilisateurs connectés dans ce POC mono-équipe).
- **`argocd-cmd-params-cm.yaml`** : active `server.insecure=true` pour exposer
  ArgoCD derrière Traefik sans TLS terminé par ArgoCD.

## Registry (`argocd/platform/registry/`)

Déploiement d'un registry `registry:2` (Docker Distribution) sans
authentification, exposé :
- **In-cluster** via un `Service ClusterIP` sur le port 5000.
- **Externe** via une `HTTPRoute` Traefik sur `registry.<domaine>`.

Pas de persistance au-delà du `PersistentVolumeClaim` local-path-provisioner —
les images sont perdues en cas de destruction du PVC.
