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

Le merge de la MR déclenche directement (sans délai) le pipeline
`.gitlab-ci.yml` de ce projet sur le runner interne, qui :
1. régénère `argocd/generated/apps/<app>/*` et `argocd/managed/apps-appset.yaml`
   (via `platform-cicd/scripts/render-argocd-apps.py`) et les commit sur ce
   même projet GitLab (le push mirror propage ensuite vers GitHub) ;
2. régénère `gitlab-projects-iac/terraform/apps.auto.tfvars.json` (via
   `toolbox/scripts/render-gitlab-projects.py`) et le commit directement sur
   GitHub (`gitlab-projects-iac` n'a pas d'équivalent GitLab) — le `Terraform`
   `gitlab-iac` (Flux) crée alors les projets GitLab `<app>`/`<app>-iac`, créés
   **vides** (pas d'import GitHub) puisque le code d'une nouvelle app n'existe
   pas encore ailleurs ; seules les apps historiques (`importFromGithub: true`,
   ex. `helloworld`) sont importées depuis un repo GitHub préexistant.

Plus besoin de lancer `make argocd-apps-render` à la main ni de toucher
`gitlab-projects-iac` : une seule MR sur `argocd/apps/` suffit. Le pipeline
utilise la variable CI/CD groupe `GITHUB_TOKEN` (groupe `infra`, déclarée dans
`gitlab-projects-iac/terraform/main.tf`, réutilise `var.github_token`) pour
cloner `platform-cicd`/`toolbox` et pousser vers GitHub, et `CI_JOB_TOKEN` pour
committer directement sur ce projet GitLab.

## Ce qu'il ne faut pas faire

- Ne pas éditer `argocd/managed/` directement.
- Ne pas éditer manuellement `argocd/generated/apps/<app>/` ; modifier
  `argocd/apps/<app>/app.yaml` puis régénérer.
- Ne pas committer de secrets non chiffrés dans ce dépôt.
- Ne pas ajouter de Job qui fabrique le contenu d'un secret `flux-secrets/*.yaml`
  au runtime : ces secrets restent des manifestes SOPS statiques. En revanche,
  un Job de copie d'un secret déjà présent en cluster vers un namespace
  applicatif (ex. `repo-creds.yaml`, `ghcr-pull-secret.yaml`) est le pattern
  attendu dans `argocd/generated/apps/<app>/`, car ArgoCD ne sait pas déchiffrer
  SOPS nativement.
- Ne pas pousser sur `main` sans avoir vérifié que `make check-generated` passe
  dans `platform-cicd`.
