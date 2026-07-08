#!/usr/bin/env python3
"""Valide les fichiers d'inventaire argocd/apps/*.yaml contre apps.schema.json.

Feedback avant merge : ce validateur tourne en CI sur les MR touchant
argocd/apps/**, pour attraper un champ inconnu (faute de frappe) ou un type
invalide avant que le rendu ArgoCD (post-merge) n'echoue. Le schema
apps.schema.json est la source de verite du contrat ; il doit rester
coherent avec platform-cicd/scripts/platform_inventory.py:_normalize_app.

Usage : validate-inventory.py [--apps-dir DIR] [--schema FILE]
Sortie non nulle si au moins un fichier est invalide.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parent.parent


def app_files(apps_dir: Path) -> list[Path]:
    # Meme decouverte que platform_inventory.load_inventory (hors index apps.yaml).
    return sorted(apps_dir.glob("*.yaml")) + sorted(apps_dir.glob("*/app.yaml"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apps-dir", type=Path, default=REPO_ROOT / "argocd/apps")
    parser.add_argument("--schema", type=Path, default=REPO_ROOT / "argocd/apps.schema.json")
    args = parser.parse_args()

    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    files = app_files(args.apps_dir.resolve())
    if not files:
        print(f"Aucun fichier d'app sous {args.apps_dir} (rien a valider).")
        return 0

    total_errors = 0
    for f in files:
        try:
            rel = f.relative_to(REPO_ROOT)
        except ValueError:
            rel = f
        try:
            doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            print(f"ERREUR {rel}: YAML invalide : {exc}", file=sys.stderr)
            total_errors += 1
            continue

        errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
        if errors:
            for e in errors:
                loc = "/".join(str(p) for p in e.path) or "(racine)"
                print(f"ERREUR {rel} [{loc}]: {e.message}", file=sys.stderr)
            total_errors += len(errors)
        else:
            print(f"OK {rel}")

    if total_errors:
        print(f"\n{total_errors} erreur(s) de validation sur {len(files)} fichier(s).", file=sys.stderr)
        return 1
    print(f"\nOK : {len(files)} fichier(s) d'inventaire valide(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
