# AGENTS.md — platform-gitops

## Rôle du dépôt

`platform-gitops` est la source de vérité GitOps de la plateforme du POC.
ArgoCD surveille ce dépôt en continu via l'Application racine
(`argocd/root-app.yaml` dans `platform-cicd`). Tout changement committé ici est
réconcilié automatiquement sur le cluster.

Le provisioning initial de la plateforme doit rester sans application. Les
ressources liées aux applications (namespaces applicatifs, credentials repo,
ApplicationSets applicatifs) sont ajoutées ensuite via `argocd/apps/<app>.yaml`,
séparément de la plateforme.

## Structure

```
argocd/
  apps.yaml              Métadonnées globales de la plateforme (domaine, registre GHCR)
  apps/
    <app>.yaml           Description source de l'application (fichier plat)
  generated/
    apps/<app>/          Manifests ArgoCD générés depuis app.yaml
  managed/               Fichiers GÉNÉRÉS — ne pas éditer à la main
    apps-appset.yaml     ApplicationSet générique qui pointe vers argocd/generated/apps/*
    gitlab.yaml          Application ArgoCD pour GitLab (chart Helm)
    platform-appset.yaml ApplicationSet pour les composants plateforme
    terraform-gitlab.yaml Application ArgoCD pour le contrôleur Terraform GitLab
    flux-source-controller.yaml Application ArgoCD pour le source-controller Flux
    tf-controller.yaml   Application ArgoCD pour le tofu-controller
    tf-crds.yaml         Application ArgoCD pour les CRDs Terraform
  platform/              Manifests des composants plateforme
    argocd-config/       ConfigMaps ArgoCD (RBAC, SSO Dex, paramètres)
    argocd-ui/           Routes HTTP ArgoCD et Dex
    gitlab/              Values Helm GitLab
    gitlab-routes/       Routes HTTP GitLab
    gitlab-minio-patch/  Patch Minio pour GitLab
    tf-controller/       Manifests du tofu-controller (exécute Terraform depuis Git)
    tf-crds/             CRDs Terraform consommées par tf-controller
flux-secrets/            Secrets Kubernetes chiffrés avec SOPS/age et appliqués par Flux
```

Il n'y a pas de registry Docker interne au cluster : les images applicatives
sont poussées sur GHCR (détail dans `docs/spec-technique.md`, section
"Registre d'images").

## Règles critiques

- **`argocd/managed/` est généré/maintenu par le bootstrap plateforme** dans
  `platform-cicd`. Ne jamais éditer ces fichiers à la main.
- **`argocd/managed/` n'est pas une couche fonctionnelle** : c'est seulement le
  point d'entrée ArgoCD généré. Il peut contenir un ApplicationSet générique
  vers `argocd/generated/apps/*`, mais pas de détails propres à une application.
- **`argocd/apps/<app>.yaml` est la source de vérité applicative**. Les
  AppProject, ApplicationSet et credentials ArgoCD de l'app sont générés dans
  `argocd/generated/apps/<app>/` via `make argocd-apps-render` depuis
  `platform-cicd`.
- **`argocd/apps.yaml`** contient les constantes de plateforme (domaine, registry,
  URL GitOps). Modifier ici impacte tous les dérivés.
- **`flux-secrets/*.yaml`** sont les seuls secrets GitOps versionnés. Ils doivent
  rester chiffrés avec SOPS/age ; ne pas recréer de Jobs bootstrap pour fabriquer
  ces secrets au runtime.

## Ajouter une application

Ouvrir une MR **sur le projet GitLab `platform-gitops`** (pas sur GitHub)
ajoutant `argocd/apps/<app>.yaml` avec au minimum :

```yaml
name: monapp
description: "Description courte de l'application"
services: [monapp-api, monapp-gui]
hasPreprod: true
```

`platform-gitops` suit le même modèle que les autres projets applicatifs
(`gitlab-projects-iac/terraform/main.tf`) : importé une fois depuis GitHub au
bootstrap, développé ensuite sur GitLab, et mirroré en continu vers GitHub
(`gitlab_project_mirror.platform_gitops_to_github`) — GitHub reste le dépôt
canonique surveillé par ArgoCD/Flux, sans changement de configuration.

Le merge de la MR déclenche automatiquement la régénération des manifests
ArgoCD et de l'inventaire Terraform `gitlab-projects-iac` : voir le détail
pas à pas dans [`docs/spec-fonctionnelle.md`](./docs/spec-fonctionnelle.md#flux-donboarding-dune-application).
Plus besoin de lancer `make argocd-apps-render` à la main ni de toucher
`gitlab-projects-iac` : une seule MR sur `argocd/apps/` suffit.

## Ce qu'il ne faut pas faire

- Ne pas éditer `argocd/managed/` directement.
- Ne pas éditer manuellement `argocd/generated/apps/<app>/` ; modifier
  `argocd/apps/<app>.yaml` puis régénérer.
- Ne pas committer de secrets non chiffrés dans ce dépôt.
- Ne pas ajouter de Job qui fabrique le contenu d'un secret `flux-secrets/*.yaml`
  au runtime : ces secrets restent des manifestes SOPS statiques. La copie ou
  la dérivation d'un secret déjà présent en cluster passe par External Secrets
  Operator (`argocd/platform/secrets-distribution/`, ExternalSecrets générés
  dans `argocd/generated/apps/<app>/`), jamais par un Job kubectl.
- Ne pas pousser sur `main` sans avoir vérifié que `make check-generated` passe
  dans `platform-cicd`.
