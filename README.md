# Pizzeria Pino — Site web

Site vitrine pour la Pizzeria Pino, Route du Condroz 131, 4550 Nandrin.

## Contenu
- `index.html` — le site (une seule page : accueil, carte interactive, galeries, contact)
- `carte/` — la carte seule, à son adresse propre, pour la recherche Google
- `statistiques/` — le tableau de bord du gérant (non indexé, protégé par mot de passe)
- `legal.html` — mentions légales, CGU, confidentialité
- `images/` — toutes les photos

## Pourquoi `/carte/` existe

La carte est le contenu le plus riche du site — 121 plats, avec prix et
composition — et elle vivait dans un onglet de la page d'accueil, sans adresse
à elle. Or une page ne peut porter qu'un seul titre : celui de l'accueil parle
du restaurant, pas de la carte ni des prix. Quelqu'un qui cherche « carte
pizzeria pino » ou « prix pizza Nandrin » a maintenant une page qui lui répond.

**La carte reste écrite une seule fois, dans `index.html`.** La page `/carte/`
en est engendrée, entre marqueurs :

```
python3 outils/carte.py              réécrit la page
python3 outils/carte.py --verifie    dit seulement si elle a divergé
python3 menu/balisage.py             réécrit le balisage Schema.org de /carte/
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
