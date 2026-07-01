# PRD — platform-gitops

## Intention du projet

`platform-gitops` est la source de vérité GitOps du POC. Il centralise l'état
déclaratif des composants plateforme (GitLab, ArgoCD, registry, contrôleurs
GitOps) et garde les ressources applicatives dans des dossiers dédiés, séparés
de la plateforme.

La vision globale de la chaîne CI/CD est dans
`../../platform-cicd/docs/prd.md`.

## Produit attendu

Le dépôt doit fournir :

- les Applications et ApplicationSets ArgoCD nécessaires aux composants
  plateforme ;
- les manifests des composants plateforme (routes, config ArgoCD, registry) ;
- un dossier `argocd/apps/<app>/` par application pour sa configuration GitOps
  dédiée ;
- les secrets plateforme chiffrés nécessaires aux contrôleurs GitOps.

## Utilisateurs cibles

- **ArgoCD** (consommateur principal) : synchronise ce dépôt en continu depuis
  l'Application racine.
- **Mainteneur plateforme** : ajoute ou modifie des composants plateforme sans
  embarquer de configuration applicative.
- **Scripts `platform-cicd`** : génèrent ou appliquent les points d'entrée
  ArgoCD de la plateforme.

## Critères d'acceptation

- Toute modification commitée sur `main` est réconciliée par ArgoCD sans
  intervention manuelle.
- `argocd/managed/` est entièrement généré et ne contient aucune configuration
  manuelle ni détail propre à une application.
- Les composants plateforme (GitLab, registry, ArgoCD config) sont déclarés dans
  `argocd/platform/` et synchronisés par ArgoCD.
- Les ressources propres aux applications sont regroupées sous
  `argocd/apps/<app>/`.

## Non-objectifs

- Contenir des secrets non chiffrés.
- Décrire la logique CI/CD applicative (portée par `ci-templates`).
- Héberger les manifests applicatifs (portés par les dépôts `*-iac` dédiés).
- Mélanger les ressources applicatives dans `argocd/platform/` ou directement
  dans `argocd/managed/`.
