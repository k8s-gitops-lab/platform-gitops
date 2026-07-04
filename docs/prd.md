# PRD — platform-gitops

## Intention du projet

`platform-gitops` est la source de vérité GitOps du POC. Il centralise l'état
déclaratif des composants plateforme (GitLab, ArgoCD, contrôleurs GitOps) et
garde les ressources applicatives dans des dossiers dédiés, séparés de la
plateforme. Les images applicatives sont poussées sur GHCR, un registre
externe non géré par ce dépôt.

La vision globale de la chaîne CI/CD est dans
`../../control-plane/docs/prd.md`.

## Produit attendu

Le dépôt doit fournir :

- les Applications et ApplicationSets ArgoCD nécessaires aux composants
  plateforme ;
- les manifests des composants plateforme (routes, config ArgoCD, GitLab) ;
- aucun dossier applicatif au provisioning initial ;
- un fichier `argocd/apps/<app>.yaml` par application après onboarding ;
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
- Les composants plateforme (GitLab, ArgoCD config) sont déclarés dans
  `argocd/platform/` et synchronisés par ArgoCD.
- Les ressources propres aux applications sont absentes au provisioning initial,
  puis générées sous `argocd/generated/apps/<app>/` après onboarding.

## Non-objectifs

- Contenir des secrets non chiffrés.
- Décrire la logique CI/CD applicative (portée par `ci-templates`).
- Héberger les manifests applicatifs (portés par les dépôts `*-iac` dédiés).
- Mélanger les ressources applicatives dans `argocd/platform/` ou directement
  dans `argocd/managed/`.
