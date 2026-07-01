# AGENTS.md — platform-gitops

## Rôle du dépôt

`platform-gitops` est la source de vérité GitOps de la plateforme du POC.
ArgoCD surveille ce dépôt en continu via l'Application racine
(`argocd/root-app.yaml` dans `platform-cicd`). Tout changement committé ici est
réconcilié automatiquement sur le cluster.

Les ressources liées aux applications (`helloworld`, `helloworld-iac`, futures
apps, namespaces applicatifs, credentials repo applicatifs, ApplicationSets
applicatifs) doivent être regroupées par application sous `argocd/apps/<app>/`,
séparément de la plateforme.

## Structure

```
argocd/
  apps.yaml              Métadonnées globales de la plateforme (domaine, registry)
  apps/
    <app>/               Configuration GitOps dédiée à une application
      app.yaml           Métadonnées applicatives
      app-project.yaml   AppProject ArgoCD de l'application
      applicationset.yaml Applications ArgoCD par environnement
      repo-creds.yaml    Credentials repo dédiés à l'application
  managed/               Fichiers GÉNÉRÉS — ne pas éditer à la main
    apps-appset.yaml     ApplicationSet générique qui pointe vers argocd/apps/*
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
  vers `argocd/apps/*`, mais pas de détails propres à une application.
- **`argocd/apps/<app>/` contient toute la configuration dédiée à une
  application**. Ne pas disperser une même app entre `managed/`, `platform/` et
  plusieurs fichiers globaux.
- **`argocd/apps.yaml`** contient les constantes de plateforme (domaine, registry,
  URL GitOps). Modifier ici impacte tous les dérivés.
- **`flux-secrets/*.yaml`** sont les seuls secrets GitOps versionnés. Ils doivent
  rester chiffrés avec SOPS/age ; ne pas recréer de Jobs bootstrap pour fabriquer
  ces secrets au runtime.

## Ajouter une application

Créer un dossier `argocd/apps/<app>/` contenant au minimum :

- `app.yaml` : métadonnées de l'application ;
- `kustomization.yaml` : liste des ressources ArgoCD dédiées ;
- `app-project.yaml` : périmètre ArgoCD de l'application ;
- `applicationset.yaml` : Applications par environnement ;
- `repo-creds.yaml` si l'application a besoin de credentials repo dédiés.

## Ce qu'il ne faut pas faire

- Ne pas éditer `argocd/managed/` directement.
- Ne pas ajouter de ressource applicative dans `argocd/platform/` ni directement
  dans `argocd/managed/` ; utiliser `argocd/apps/<app>/`.
- Ne pas committer de secrets non chiffrés dans ce dépôt.
- Ne pas ajouter de Job qui lit un secret root pour générer un autre secret :
  préférer un manifeste SOPS dans `flux-secrets/`.
- Ne pas pousser sur `main` sans avoir vérifié que `make check-generated` passe
  dans `platform-cicd`.
