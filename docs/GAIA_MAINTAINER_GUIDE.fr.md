# Gérer le dépôt HoopcareAI-ECG

Ce dépôt public contient le code de recherche destiné à être partagé. Les données patients, poids du modèle et outils internes restent dans leurs espaces autorisés.

## Ton accès

Le compte GitHub de Gaia est `gbensouda`. Le rôle **Maintain** est activé sur `hoopcare/HoopcareAI-ECG` : gestion quotidienne des branches, pull requests, issues et releases. Les changements d’accès, de visibilité ou de licence se coordonnent avec l’administrateur de l’organisation.

## Première installation

```bash
git clone https://github.com/hoopcare/HoopcareAI-ECG.git
cd HoopcareAI-ECG
```

Lis le README de `analysis/mimic_iv_surgical` avant de lancer une analyse. Installe les dépendances dans un environnement séparé et conserve les données et résultats individuels hors de ce dossier Git.

## Une mise à jour ordinaire

```bash
git switch main
git pull --ff-only
git switch -c gaia/description-courte
```

Fais la modification, puis lance les contrôles dans un environnement Python séparé (Python 3.12 et Node 24) :

```bash
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -p 'test*.py'
node --test tests/test_demo*.cjs
```

Vérifie précisément les fichiers concernés :

```bash
git diff --check
git diff
git status --short
```

Ajoute uniquement les fichiers voulus, avec leurs chemins explicites. Vérifie ensuite `git diff --cached` avant le commit. Exemple pour une correction de documentation :

```bash
git add README.md
git diff --cached
python tools/check_public_tree.py --root .
git commit -m "docs: clarify analysis prerequisites"
git push -u origin gaia/description-courte
gh pr create --fill
gh pr checks --watch
```

Dans la pull request, explique ce qui change, les vérifications faites et si les résultats scientifiques peuvent changer. Lorsque les contrôles sont verts et la modification revue, fusionne avec **Squash and merge** sur GitHub. Une mise à jour ordinaire ne nécessite pas de demander à Yassine de la faire à ta place.

## Publier une version

Après fusion et réussite des contrôles de `main`, crée une release depuis GitHub → **Releases** → **Draft a new release**. Choisis un nouveau tag et décris les changements et les limites de reproduction. N’ajoute que des fichiers dont la diffusion publique est autorisée.

Ne présente pas une version comme celle de l’article avant d’avoir relié précisément le tag aux analyses concernées. Lors de la publication de l’article, complète `CITATION.cff` avec les métadonnées vérifiées.

## Ce qui demande une vérification particulière

- **Définition scientifique** : documenter tout changement de population, fenêtre temporelle, outcome, seuil, calibration ou méthode statistique.
- **Nouveau code issu d’un autre dépôt** : vérifier les droits de redistribution et conserver sa licence.
- **Données, prédictions individuelles ou poids** : ne pas les ajouter au dépôt, même pour déboguer.
- **Licence et accès** : la licence est limitée à la recherche non commerciale ; un usage commercial nécessite un accord séparé.

Pour signaler un problème avec un script, utiliser un exemple synthétique. Ne pas coller un compte-rendu clinique, une image d’ECG ou un journal contenant des identifiants dans une issue.
