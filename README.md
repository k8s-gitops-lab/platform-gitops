# platform-gitops

Configuration GitOps synchronisee par ArgoCD pour le POC.

Ce depot contient l'etat plateforme suivi en continu par ArgoCD :

- `argocd/managed/` : Applications ArgoCD generees pour amorcer les composants plateforme.
- `argocd/platform/` : manifests des composants plateforme.
- `argocd/apps/` : un fichier plat `<app>.yaml` par application, comme
  description source.
- `argocd/generated/apps/` : manifests ArgoCD générés depuis les descriptions
  applicatives.
- `argocd/apps.yaml` : constantes globales de plateforme conservees pour les generateurs.
- `flux-secrets/` : secrets Kubernetes chiffrés avec SOPS/age, déchiffrés et
  appliqués par Flux.

Le provisioning initial de la plateforme ne contient aucune application. Les
ressources applicatives sont ajoutées ensuite sous `argocd/apps/<app>.yaml`,
puis générées sous `argocd/generated/apps/<app>/`. Elles ne doivent pas être
mélangées à `argocd/platform/`.

Le bootstrap technique reste dans `../platform-bootstrap` : installation ArgoCD,
configuration initiale et commandes operateur.
