#!/usr/bin/env python3
"""
Injecte la liste des localités dans les fichiers qui en ont besoin.

Sources : mesure/lieux.json et mesure/geo.json

mesure/lieux.json — relevé OpenStreetMap : les localités
dans un rayon de 20 km autour de Nandrin, plus les villes et bourgs belges.

Un destinataire :
  statistiques/index.html les lieux, leurs coordonnées, l'index des graphies
                     repliées qui permet d'y retrouver ce que le service de
                     géolocalisation renvoie, et le contour du pays

Les blocs sont délimités par des marqueurs et réécrits en entier ; on ne les
modifie pas à la main. Relancer après toute mise à jour de lieux.json :

    python3 mesure/lieux.py
"""
import json
import os
import re
import sys
import unicodedata

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def pliage(v):
    """Une graphie comparable : sans accent, sans ponctuation, en minuscules."""
    v = unicodedata.normalize('NFD', str(v).strip().lower())
    v = ''.join(c for c in v if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z]+', '', v)


def charge():
    with open(os.path.join(RACINE, 'mesure', 'lieux.json'), encoding='utf-8') as f:
        return json.load(f)


def remplace(chemin, debut, fin, contenu):
    """Réécrit ce qui se trouve entre les deux marqueurs, marqueurs compris."""
    complet = os.path.join(RACINE, chemin)
    with open(complet, encoding='utf-8') as f:
        s = f.read()
    if debut not in s or fin not in s:
        print('  ignoré (marqueurs absents) : %s' % chemin)
        return False
    i = s.index(debut)
    j = s.index(fin) + len(fin)
    neuf = s[:i] + debut + '\n' + contenu + '\n' + fin + s[j:]
    if neuf == s:
        print('  inchangé : %s' % chemin)
        return False
    with open(complet, 'w', encoding='utf-8') as f:
        f.write(neuf)
    print('  réécrit  : %s' % chemin)
    return True


def main():
    d = charge()
    lieux = d['lieux']
    print('%d localités, centre %s' % (len(lieux), d['_centre']['nom']))

    # ── statistiques/index.html : les coordonnées de la carte ─────────────────
    # Un tableau des lieux, et un index des graphies repliées (sans accent ni
    # ponctuation) qui pointe vers eux. Le service de géolocalisation écrit
    # « Ferrieres » pour Ferrières et « Dendermonde » pour Termonde : sans cet
    # index, ces visites ne se placeraient nulle part.
    c = d['_centre']
    tableau, index = [], {}
    for i, l in enumerate(lieux):
        tableau.append('[%s,%s,%s]' % (l['lat'], l['lon'],
                                       json.dumps(l['nom'], ensure_ascii=False)))
        for n in [l['nom']] + l.get('aussi', []):
            k = pliage(n)
            if k and k not in index:
                index[k] = i

    def enroule(morceaux, largeur=98, creux='    '):
        lignes, ligne = [], creux
        for m in morceaux:
            if len(ligne) + len(m) > largeur:
                lignes.append(ligne.rstrip())
                ligne = creux
            ligne += m + ','
        lignes.append(ligne.rstrip().rstrip(','))
        return '\n'.join(lignes)

    js = ('  /* Lieux et coordonnées, relevés sur OpenStreetMap (ODbL). */\n'
          '  var CENTRE = [%s, %s];\n'
          '  var LIEUX = [\n%s\n  ];\n'
          '  var INDEX = {\n%s\n  };'
          % (c['lat'], c['lon'],
             enroule(tableau),
             enroule('%s:%d' % (json.dumps(k, ensure_ascii=False), v)
                     for k, v in sorted(index.items()))))
    remplace('statistiques/index.html',
             '  /* lieux:début — engendré par mesure/lieux.py, ne pas modifier à la main */',
             '  /* lieux:fin */',
             js)

    # ── le contour du pays, pour que la carte ressemble a une carte ──────
    with open(os.path.join(RACINE, 'mesure', 'geo.json'), encoding='utf-8') as f:
        geo = json.load(f)
    anneaux = []
    for anneau in geo['belgique']:
        pts = ['[%s,%s]' % (x, y) for x, y in anneau]
        anneaux.append('    [' + ','.join(pts) + ']')
    pays = ('  /* Contour de la Belgique (Natural Earth, domaine public). Coordonnées\n'
            '     brutes en degrés — longitude puis latitude — projetées au tracé,\n'
            '     exactement comme les bulles, pour que tout reste superposable. */\n'
            '  var PAYS = [\n%s\n  ];' % ',\n'.join(anneaux))
    remplace('statistiques/index.html',
             '  /* pays:début — engendré par mesure/lieux.py, ne pas modifier à la main */',
             '  /* pays:fin */',
             pays)
    return 0


if __name__ == '__main__':
    sys.exit(main())
