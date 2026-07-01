# Spec technique — platform-gitops

## Structure du dépôt

```
argocd/
  apps.yaml                    Métadonnées globales (domaine, registry, repoURL GitOps)
  apps/
    helloworld/
      app.yaml                 Métadonnées de l'application
      app-project.yaml         AppProject ArgoCD dédié
      applicationset.yaml      Applications ArgoCD par environnement
      repo-creds.yaml          Credentials repo dédiés
  managed/                     GÉNÉRÉ — ne pas éditer à la main
    apps-appset.yaml           ApplicationSet générique vers argocd/apps/*
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
  gitlab-tf-credentials.yaml  Secret Terraform chiffré SOPS pour piloter GitLab/GitHub
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
applicatif détaillé. Les ressources d'une application doivent être regroupées
dans `argocd/apps/<app>/`.

## Secrets GitOps (`flux-secrets/`)

Les secrets applicatifs nécessaires aux contrôleurs GitOps sont versionnés sous
forme chiffrée avec SOPS/age dans `flux-secrets/`.

| Secret Kubernetes | Fichier | Consommateur |
|-------------------|---------|--------------|
| `github-credentials` | `flux-secrets/github-credentials.yaml` | `GitRepository/gitlab-projects-iac` et `Terraform/gitlab-iac` |
| `gitlab-tf-credentials` | `flux-secrets/gitlab-tf-credentials.yaml` | `Terraform/gitlab-iac` |

Flux applique ces secrets via `argocd/platform/tf-controller/flux-secrets-kustomization.yaml`
avec `decryption.provider: sops` et `secretRef.name: sops-age`. Le secret
`sops-age` reste un prérequis de bootstrap : il contient la clé privée age et ne
doit pas être committé.

Ce modèle remplace le Job impératif qui lisait le mot de passe root GitLab pour
fabriquer `gitlab-tf-credentials` au runtime. La rotation se fait maintenant en
éditant le manifeste avec `sops`, puis en laissant Flux réconcilier le secret.
Si l'instance GitLab est recréée sans conserver sa base de données, ce PAT doit
être régénéré dans GitLab puis rechiffré dans `gitlab-tf-credentials.yaml`.

## `argocd/managed/` — point d'entrée généré

`argocd/managed/` contient les objets ArgoCD que l'Application racine applique
pour amorcer la plateforme : GitLab, Flux/tofu-controller, CRDs Terraform et
ApplicationSet des composants plateforme. Il contient aussi l'ApplicationSet
générique `apps-appset.yaml`, qui découvre les dossiers `argocd/apps/*` et crée
une Application ArgoCD par dossier applicatif.

Ce répertoire n'est pas une couche métier distincte de `argocd/platform/` :
- `argocd/platform/` contient les manifests sources des composants plateforme ;
- `argocd/managed/` contient les Applications ArgoCD générées qui pointent vers
  ces manifests.

Il ne doit pas contenir d'`AppProject`, `Application`, `ApplicationSet`,
credential ou namespace propre à une application. Ces objets doivent être dans
`argocd/apps/<app>/`.

## `argocd/apps/<app>/` — configuration dédiée par application

Chaque application possède un dossier autonome. Pour `helloworld` :

| Fichier | Rôle |
|---------|------|
| `app.yaml` | Métadonnées de l'application et de ses dépôts code/IaC |
| `app-project.yaml` | Périmètre ArgoCD autorisé pour l'application |
| `applicationset.yaml` | Applications ArgoCD `dev`, `rec`, `preprod`, `prod` |
| `repo-creds.yaml` | Secret ArgoCD/RBAC dédiés au dépôt manifests de l'app |
| `kustomization.yaml` | Agrège les ressources dédiées à l'application |

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
