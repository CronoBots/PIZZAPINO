#!/usr/bin/env python3
"""
Associe chaque plat de la carte à sa catégorie, pour le tableau de bord.

La base n'enregistre que des intitulés de plats : « Pizza Capricciosa »,
« Spaghetti Carbonara ». Elle ignore à quelle section de la carte ils
appartiennent. Ce script lit index.html et en tire la correspondance, qu'il
injecte dans aldente/index.html entre deux marqueurs.

Un piège à reproduire fidèlement : un script de la page ajoute « Pizza »
devant les noms du panneau pizzas — mais il s'arrête à la section
« Pizza Bianca ». Le panier relève le nom APRÈS cette réécriture, donc c'est
ce nom-là qui arrive en base. Se tromper ici, c'est ranger la moitié des
pizzas dans « inconnu ».

    python3 mesure/plats.py
"""
import json
import os
import re
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NOM = re.compile(r'<span class="name">([^<]+)</span>')
PANNEAU = re.compile(r'<div class="menu-panel[^"]*" id="([a-z]+)">')
TITRE = re.compile(r'class="cat-title"[^>]*>([^<]*)', re.I)


def plats_par_categorie(html):
    """{ nom tel qu'il arrive en base : catégorie }."""
    table = {}
    bornes = [(m.group(1), m.end()) for m in PANNEAU.finditer(html)]
    for i, (cat, debut) in enumerate(bornes):
        fin = bornes[i + 1][1] if i + 1 < len(bornes) else len(html)
        bloc = html[debut:fin]

        # Le préfixe « Pizza » cesse à la section Bianca : on cherche où.
        coupure = len(bloc)
        if cat == 'pizzas':
            for t in TITRE.finditer(bloc):
                if 'bianca' in t.group(1).lower():
                    coupure = t.start()
                    break

        for m in NOM.finditer(bloc):
            nom = m.group(1).strip()
            if cat == 'pizzas' and m.start() < coupure and not re.match(r'^pizza\b', nom, re.I):
                nom = 'Pizza ' + nom
            table.setdefault(nom, cat)
    return table


def remplace(chemin, debut, fin, contenu):
    complet = os.path.join(RACINE, chemin)
    with open(complet, encoding='utf-8') as f:
        s = f.read()
    if debut not in s or fin not in s:
        print('  ignoré (marqueurs absents) : %s' % chemin)
        return False
    i, j = s.index(debut), s.index(fin) + len(fin)
    neuf = s[:i] + debut + '\n' + contenu + '\n' + fin + s[j:]
    if neuf == s:
        print('  inchangé : %s' % chemin)
        return False
    with open(complet, 'w', encoding='utf-8') as f:
        f.write(neuf)
    print('  réécrit  : %s' % chemin)
    return True


def main():
    with open(os.path.join(RACINE, 'index.html'), encoding='utf-8') as f:
        table = plats_par_categorie(f.read())

    from collections import Counter
    print('%d plats : %s' % (len(table), dict(Counter(table.values()))))

    paires = ['%s:%s' % (json.dumps(n, ensure_ascii=False), json.dumps(c))
              for n, c in sorted(table.items())]
    lignes, ligne = [], '    '
    for p in paires:
        if len(ligne) + len(p) > 100:
            lignes.append(ligne.rstrip())
            ligne = '    '
        ligne += p + ','
    lignes.append(ligne.rstrip().rstrip(','))

    js = ('  /* Plat → section de la carte, engendré depuis index.html.\n'
          '     Les noms sont ceux qui arrivent en base, préfixe « Pizza » compris. */\n'
          '  var PLATS = {\n%s\n  };' % '\n'.join(lignes))
    remplace('aldente/index.html',
             '  /* plats:début — engendré par mesure/plats.py, ne pas modifier à la main */',
             '  /* plats:fin */',
             js)
    return 0


if __name__ == '__main__':
    sys.exit(main())
