# AGENTS.md — platform-gitops

## Rôle du dépôt

`platform-gitops` est la source de vérité GitOps de la plateforme du POC.
ArgoCD surveille ce dépôt en continu via l'Application racine
(`argocd/root-app.yaml` dans `platform-cicd`). Tout changement committé ici est
réconcilié automatiquement sur le cluster.

Le provisioning initial de la plateforme doit rester sans application. Les
ressources liées aux applications (namespaces applicatifs, credentials repo,
ApplicationSets applicatifs) sont ajoutées ensuite sous `argocd/apps/<app>/`,
séparément de la plateforme.

## Structure

```
argocd/
  apps.yaml              Métadonnées globales de la plateforme (domaine, registry)
  apps/
    <app>/               Configuration GitOps dédiée à une application
      app.yaml           Description source de l'application
  generated/
    apps/<app>/          Manifests ArgoCD générés depuis app.yaml
  managed/               Fichiers GÉNÉRÉS — ne pas éditer à la main
    apps-appset.yaml     ApplicationSet générique qui pointe vers argocd/generated/apps/*
    gitlab.yaml          Application ArgoCD pour GitLab
    platform-appset.yaml ApplicationSet pour les composants plateforme
    terraform-gitlab.yaml Application ArgoCD pour le contrôleur Terraform GitLab
  platform/              Manifests des composants plateforme
    argocd-config/       ConfigMaps ArgoCD (RBAC, SSO Dex, paramètres)
    argocd-ui/           Routes HTTP ArgoCD et Dex
    gitlab-routes/       Routes HTTP GitLab
    gitlab-minio-patch/  Patch Minio pour GitLab
    registry/            Déploiement du registry Docker interne
flux-secrets/            Secrets Kubernetes chiffrés avec SOPS/age et appliqués par Flux
```

## Règles critiques

- **`argocd/managed/` est généré/maintenu par le bootstrap plateforme** dans
  `platform-cicd`. Ne jamais éditer ces fichiers à la main.
- **`argocd/managed/` n'est pas une couche fonctionnelle** : c'est seulement le
  point d'entrée ArgoCD généré. Il peut contenir un ApplicationSet générique
  vers `argocd/generated/apps/*`, mais pas de détails propres à une application.
- **`argocd/apps/<app>/app.yaml` est la source de vérité applicative**. Les
  AppProject, ApplicationSet et credentials ArgoCD de l'app sont générés dans
  `argocd/generated/apps/<app>/` via `make argocd-apps-render` depuis
  `platform-cicd`.
- **`argocd/apps.yaml`** contient les constantes de plateforme (domaine, registry,
  URL GitOps). Modifier ici impacte tous les dérivés.
- **`flux-secrets/*.yaml`** sont les seuls secrets GitOps versionnés. Ils doivent
  rester chiffrés avec SOPS/age ; ne pas recréer de Jobs bootstrap pour fabriquer
  ces secrets au runtime.

## Ajouter une application

Ouvrir une PR ajoutant `argocd/apps/<app>.yaml` avec au minimum :

```yaml
name: monapp
description: "Description courte de l'application"
services: [monapp-api, monapp-gui]
hasPreprod: true
```

Ce dépôt est mergé sur GitHub, mais l'automatisation tourne côté GitLab : le
projet GitLab `platform-gitops` (`gitlab-projects-iac`) est un mirror pull
continu depuis GitHub (`mirror_trigger_builds = true`), donc chaque merge sur
`main` déclenche le pipeline `.gitlab-ci.yml` de ce dépôt sur le runner interne.
Ce pipeline :
1. régénère `argocd/generated/apps/<app>/*` et `argocd/managed/apps-appset.yaml`
   (via `platform-cicd/scripts/render-argocd-apps.py`) et les commit
   directement sur `main` **sur GitHub** (le mirror GitLab n'est jamais un
   cible de push, il serait écrasé au prochain pull) ;
2. régénère `gitlab-projects-iac/terraform/apps.auto.tfvars.json` (via
   `toolbox/scripts/render-gitlab-projects.py`) et le commit sur ce dépôt
   (GitHub) — le `Terraform` `gitlab-iac` (Flux) crée alors les projets GitLab
   `<app>`/`<app>-iac`.

Plus besoin de lancer `make argocd-apps-render` à la main ni de toucher
`gitlab-projects-iac` : une seule PR sur `argocd/apps/` suffit. Le pipeline
utilise la variable CI/CD groupe `GITHUB_TOKEN` (groupe `infra`, déclarée dans
`gitlab-projects-iac/terraform/main.tf`, réutilise `var.github_token`) pour
cloner `platform-cicd`/`toolbox` et pousser vers GitHub.

## Ce qu'il ne faut pas faire

- Ne pas éditer `argocd/managed/` directement.
- Ne pas éditer manuellement `argocd/generated/apps/<app>/` ; modifier
  `argocd/apps/<app>/app.yaml` puis régénérer.
- Ne pas committer de secrets non chiffrés dans ce dépôt.
- Ne pas ajouter de Job qui lit un secret root pour générer un autre secret :
  préférer un manifeste SOPS dans `flux-secrets/`.
- Ne pas pousser sur `main` sans avoir vérifié que `make check-generated` passe
  dans `platform-cicd`.
