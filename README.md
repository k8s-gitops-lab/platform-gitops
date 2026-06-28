# platform-gitops

Configuration GitOps synchronisee par ArgoCD pour le POC.

Ce depot contient l'etat applicatif suivi en continu par ArgoCD :

- `argocd/managed/` : root app-of-apps, composants plateforme et ApplicationSets.
- `argocd/platform/` : manifests des composants plateforme.
- `argocd/apps.yaml` et `argocd/apps/` : inventaire applicatif.

Le bootstrap technique reste dans `../platform-cicd` : installation ArgoCD,
configuration initiale et commandes operateur.
