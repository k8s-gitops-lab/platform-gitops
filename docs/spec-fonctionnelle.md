# Spec fonctionnelle — platform-gitops

## Modèle de synchronisation ArgoCD

ArgoCD surveille ce dépôt via l'Application racine (`root`) appliquée une
seule fois à la main depuis `platform-cicd`. Cette Application cible
`argocd/managed/` sur la branche `main`.

Tout ce qui se trouve dans `argocd/managed/` est donc géré par ArgoCD :
modifications committées → réconciliation automatique sur le cluster.

`argocd/managed/` n'est pas une séparation fonctionnelle. C'est une sortie
générée qui contient les objets ArgoCD d'amorçage. Il peut contenir un
ApplicationSet générique qui pointe vers `argocd/apps/*`, mais les détails d'une
application restent dans son dossier dédié.

## Composants plateforme (`argocd/platform/`)

| Dossier | Contenu |
|---------|---------|
| `argocd-config/` | `argocd-cm.yaml` (Dex OIDC), `argocd-rbac-cm.yaml`, `argocd-cmd-params-cm.yaml` |
| `argocd-ui/` | HTTPRoute ArgoCD, HTTPRoute Dex, Service NodePort Dex |
| `gitlab-routes/` | HTTPRoutes GitLab (UI, registry, SSH) |
| `gitlab-minio-patch/` | Patch Kustomize pour les buckets Minio GitLab |
| `registry/` | Déploiement, Service et HTTPRoute du registry Docker |

## Flux d'onboarding d'une application

L'onboarding applicatif ajoute un dossier `argocd/apps/<app>/` qui regroupe
toute la configuration GitOps dédiée à l'application : métadonnées, AppProject,
ApplicationSet par environnement et éventuels credentials repo. Le reste du
seed applicatif reste porté par `toolbox`/les outils de seed pour créer les
projets GitLab et les dépôts `*-iac`.

## Promotion des applications

Les branches d'environnement (`dev`, `rec`, `preprod`) du dépôt manifests
(`*-iac`) sont mises à jour par la CI applicative via `deploy.py`. Ce dépôt ne
porte pas la logique de promotion ; il déclare seulement, dans
`argocd/apps/<app>/`, les branches applicatives suivies par ArgoCD.
