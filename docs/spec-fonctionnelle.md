# Spec fonctionnelle — platform-gitops

## Modèle de synchronisation ArgoCD

ArgoCD surveille ce dépôt via l'Application racine (`root`) appliquée une
seule fois à la main depuis `platform-bootstrap`. Cette Application cible
`argocd/managed/` sur la branche `main`.

Tout ce qui se trouve dans `argocd/managed/` est donc géré par ArgoCD :
modifications committées → réconciliation automatique sur le cluster.

Au provisioning initial, aucune application n'est déclarée : `argocd/apps/` et
`argocd/generated/apps/` restent vides. Les applications sont ajoutées après la
plateforme, une fois les projets GitLab provisionnés par Terraform.

`argocd/managed/` n'est pas une séparation fonctionnelle. C'est une sortie
générée qui contient les objets ArgoCD d'amorçage. Il peut contenir un
ApplicationSet générique qui pointe vers `argocd/generated/apps/*`, mais les
détails d'une application viennent de sa description `argocd/apps/<app>.yaml`.

## Composants plateforme (`argocd/platform/`)

| Dossier | Contenu |
|---------|---------|
| `argocd-config/` | `argocd-cm.yaml`, `argocd-rbac-cm.yaml`, `argocd-cmd-params-cm.yaml` — pas de SSO (décommissionné, cf. `docs/backlog.md`) |
| `argocd-ui/` | HTTPRoute ArgoCD (login local `admin` uniquement) |
| `gitlab-runner-com/` | Values Helm du runner gitlab.com + CA Zscaler |
| `tf-controller/` | Manifests du tofu-controller (exécute Terraform depuis Git) |
| `tf-crds/` | CRDs Terraform consommées par tf-controller |

Il n'y a pas de dossier `registry/` : les images applicatives sont poussées
sur GHCR, pas sur un registry interne au cluster (voir "Registre d'images"
dans `docs/spec-technique.md`).

## Flux d'onboarding d'une application

L'onboarding applicatif ajoute un fichier `argocd/apps/<app>.yaml`, la
description source de l'application : nom, description, modules/services,
environnements optionnels. Les MR se font directement sur le projet GitLab
`platform-gitops` (importé une fois depuis GitHub, puis développé et mirroré
en continu vers GitHub comme les autres projets applicatifs). Le merge sur
`main` déclenche directement le pipeline `.gitlab-ci.yml` de ce projet, qui :

1. génère les AppProject, ApplicationSet par environnement et credentials repo
   sous `argocd/generated/apps/<app>/` (via `platform-bootstrap/scripts/render-argocd-apps.py`)
   et les commit sur ce même projet GitLab (le push mirror propage vers GitHub) ;
2. génère `gitlab-projects-iac/terraform/apps.auto.tfvars.json` (via
   `toolbox/scripts/render-gitlab-projects.py`) et le commit directement sur
   GitHub.

La création des projets GitLab et des dépôts `*-iac` n'est plus portée par
`toolbox`. Elle est déclarée (désormais automatiquement) dans le dépôt
`gitlab-projects-iac` et appliquée par le `Terraform/gitlab-iac` exécuté par
tf-controller. Les nouvelles apps sont créées vides sur GitLab (pas d'import
GitHub, leur code n'existe pas encore ailleurs) ; seules les apps historiques
marquées `importFromGithub: true` importent un contenu préexistant. Aucune
étape manuelle n'est requise après le merge de la MR.

## Promotion des applications

Les branches d'environnement (`dev`, `rec`, `preprod`) du dépôt manifests
(`*-iac`) sont mises à jour par la CI applicative via `deploy.py`. Ce dépôt ne
porte pas la logique de promotion ; il déclare seulement, via `app.yaml`, les
branches applicatives suivies par ArgoCD. Le contenu des dépôts applicatifs et
les variables nécessaires aux pipelines doivent être initialisés par les jobs
CI/CD applicatifs prévus pour cela.
