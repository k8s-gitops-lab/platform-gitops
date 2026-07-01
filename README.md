# platform-gitops

Configuration GitOps synchronisee par ArgoCD pour le POC.

Ce depot contient l'etat plateforme suivi en continu par ArgoCD :

- `argocd/managed/` : Applications ArgoCD generees pour amorcer les composants plateforme.
- `argocd/platform/` : manifests des composants plateforme.
- `argocd/apps/` : un repertoire par application, avec toute la configuration
  GitOps dediee a cette application.
- `argocd/apps.yaml` : constantes globales de plateforme conservees pour les generateurs.
- `flux-secrets/` : secrets Kubernetes chiffrés avec SOPS/age, déchiffrés et
  appliqués par Flux.

Les ressources applicatives (`helloworld`, `helloworld-iac`, etc.) sont
séparées de la plateforme par dossier sous `argocd/apps/<app>/`. Elles ne
doivent pas être mélangées à `argocd/platform/`.

Le bootstrap technique reste dans `../platform-cicd` : installation ArgoCD,
configuration initiale et commandes operateur.
