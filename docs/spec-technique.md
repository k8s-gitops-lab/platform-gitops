# Spec technique — platform-gitops

## Structure du dépôt

```
.gitlab-ci.yml                 Pipeline GitLab : régénère argocd/generated/ et gitlab-projects-iac au merge d'une app
argocd/
  apps.yaml                    Métadonnées globales (domaine, registre GHCR, repoURL GitOps)
  apps/                        Descriptions applicatives ajoutées après bootstrap
  generated/apps/              Manifests ArgoCD générés après onboarding app
  managed/                     GÉNÉRÉ — ne pas éditer à la main
    apps-appset.yaml           ApplicationSet générique vers argocd/generated/apps/*
    gitlab.yaml                Application ArgoCD pour GitLab (chart Helm)
    platform-appset.yaml       ApplicationSet pour les composants plateforme
    terraform-gitlab.yaml      Application ArgoCD pour le contrôleur Terraform GitLab
    flux-source-controller.yaml Application ArgoCD pour le source-controller Flux
    tf-controller.yaml         Application ArgoCD pour le tofu-controller
    tf-crds.yaml                Application ArgoCD pour les CRDs Terraform
  platform/                    Manifests des composants plateforme
    argocd-config/             Kustomization : argocd-cm, argocd-rbac-cm, argocd-cmd-params-cm
    argocd-ui/                 HTTPRoutes ArgoCD et Dex
    gitlab/                    Values Helm GitLab (bootstrap)
    gitlab-routes/             HTTPRoutes GitLab
    gitlab-minio-patch/        Patch Kustomize Minio
    tf-controller/             Manifests du tofu-controller
    tf-crds/                   CRDs Terraform consommées par tf-controller
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
  repoURL: https://github.com/k8s-gitops-lab/platform-gitops
  targetRevision: main
  registry:
    host: ghcr.io/k8s-gitops-lab

gitlab:
  internalHost: gitlab-webservice-default.gitlab.svc.cluster.local:8181

appsDir: apps
```

`repoURL` est l'URL externe (GitHub) utilisée pour le bootstrapping initial
d'ArgoCD. Une fois GitLab opérationnel, ArgoCD peut être reconfiguré pour
pointer vers l'instance GitLab interne.

Malgré son nom historique, ce fichier ne doit pas devenir un inventaire
applicatif détaillé. Les ressources d'une application doivent être décrites dans
`argocd/apps/<app>.yaml`.

## Secrets GitOps (`flux-secrets/`)

Les secrets applicatifs nécessaires aux contrôleurs GitOps sont versionnés sous
forme chiffrée avec SOPS/age dans `flux-secrets/`.

| Secret Kubernetes | Fichier | Consommateur |
|-------------------|---------|--------------|
| `github-credentials` | `flux-secrets/github-credentials.yaml` | `GitRepository/gitlab-projects-iac` et `Terraform/gitlab-iac` |
| `ghcr-pull-secret` | `flux-secrets/ghcr-pull-secret.yaml` | Secret source GHCR (namespace `argocd`), distribué par External Secrets Operator |

Flux applique ces secrets via `argocd/platform/tf-controller/flux-secrets-kustomization.yaml`
avec `decryption.provider: sops` et `secretRef.name: sops-age`. Le secret
`sops-age` reste un prérequis de bootstrap : il contient la clé privée age et ne
doit pas être committé.

Le secret source `ghcr-pull-secret` (pull d'images depuis GHCR) est généré par
`control-plane make ghcr-token-init`, déposé dans le namespace `argocd` par la
Kustomization Flux ci-dessus, puis distribué en continu sous le nom `ghcr-pull`
par External Secrets Operator (`argocd/platform/secrets-distribution/`) dans
tout namespace portant le label `k8s-gitops-lab.io/ghcr-pull=enabled` — label
posé par les `Namespace` générés dans `argocd/generated/apps/<app>/namespaces.yaml`.

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
`argocd/generated/apps/<app>/` et générés depuis `argocd/apps/<app>.yaml`.

## `argocd/apps/<app>.yaml` — description applicative

Le dépôt est livré sans application déclarée pour que le provisioning plateforme
reste indépendant. Après provisioning, chaque application possède une
description source, écrite à la main et proposée par pull/merge request
directe. Le format est défini par le JSON Schema `argocd/apps.schema.json`
(source de vérité du contrat) : seuls `name` et `group` sont requis, tout le
reste est dérivé par convention (voir
`platform-cicd/scripts/platform_inventory.py`). `apiVersion: platform/v1`
versionne le contrat. Une MR touchant `argocd/apps/**` est validée en CI
contre ce schéma (job `validate-inventory`, `scripts/validate-inventory.py`)
— un champ inconnu ou un type invalide échoue avant le merge :

| Fichier | Rôle |
|---------|------|
| `argocd/apps/<app>.yaml` | Nom, description, modules/services, dépôt code et dépôt IaC |
| `argocd/generated/apps/<app>/app-project.yaml` | Périmètre ArgoCD autorisé, généré (inclut `spec.description`) |
| `argocd/generated/apps/<app>/applicationset.yaml` | Applications ArgoCD par environnement, générées |
| `argocd/generated/apps/<app>/namespaces.yaml` | Namespaces d'environnement labellisés pour la distribution du secret `ghcr-pull` par External Secrets, générés |
| `argocd/generated/apps/<app>/repo-creds.yaml` | ExternalSecret qui fabrique le secret repository ArgoCD du dépôt manifests de l'app, généré |
| `argocd/generated/apps/<app>/kustomization.yaml` | Agrège les ressources générées |

Depuis l'ajout du pipeline `.gitlab-ci.yml` (projet GitLab `platform-gitops`),
la génération n'est plus une étape manuelle : elle se déclenche automatiquement
au merge d'une MR touchant `argocd/apps/**`. `make argocd-apps-render` /
`make check-generated` (depuis `platform-cicd`) restent disponibles pour
vérifier ou régénérer en local :

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

## Registre d'images (GHCR)

Il n'y a pas de registry Docker déployé dans le cluster. `argocd/apps.yaml`
déclare `registry.host: ghcr.io/k8s-gitops-lab` : c'est la valeur
consommée par `platform_inventory.py` pour construire les références
d'image des apps. Le secret de pull source (`ghcr-pull-secret`) vit chiffré
dans `flux-secrets/` et est distribué par External Secrets Operator (voir
"Secrets GitOps" ci-dessus).
