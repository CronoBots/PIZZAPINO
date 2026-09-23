# Pizzeria Pino — Site web

Site vitrine pour la Pizzeria Pino, Route du Condroz 131, 4550 Nandrin.

## Contenu
- `index.html` — le site (une seule page : accueil, carte interactive, galeries, contact)
- `statistiques/` — le tableau de bord du gérant (non indexé, protégé par mot de passe)
- `legal.html` — mentions légales, CGU, confidentialité
- `images/` — toutes les photos

## La carte et le scan du menu

La carte est écrite une seule fois, dans `index.html` : c'est la source. Le
scan du menu officiel vit dans `menu/`, hors de l'index, et un contrôle dit si
le site s'en est écarté.

```
python3 menu/balisage.py             réécrit le balisage Schema.org de la carte
python3 menu/balisage.py --verifie   dit seulement s'il a divergé
python3 menu/verifie.py              compare le site au scan du menu officiel
```

**À relancer après toute modification de la carte dans `index.html`** — un prix
changé d'un côté et pas de l'autre, et le client arrive avec un tarif périmé.

## Mise en ligne sur GitHub Pages
1. Pousser ces fichiers à la racine du dépôt.
2. Aller dans **Settings → Pages**.
3. Sous "Source", choisir la branche `main` et le dossier `/ (root)`.
4. Enregistrer. Le site sera en ligne sous quelques minutes à l'adresse indiquée.

## À personnaliser avant la version définitive
- Remplacer les photos du dossier `images/` par les vraies photos du restaurant.
- Vérifier la carte et les prix.

## Technique
- HTML / CSS / JavaScript natifs, aucune dépendance.
- Responsive (mobile, tablette, ordinateur).
- Optimisé SEO (Open Graph, données structurées Schema.org, lazy-loading).
