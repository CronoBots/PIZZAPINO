#!/usr/bin/env python3
"""
Injecte la liste des localités dans les fichiers qui en ont besoin.

Source unique : mesure/lieux.json — relevé OpenStreetMap des localités
(place=city|town|village) dans un rayon de 20 km autour de Nandrin.

Deux destinataires, deux formes :
  index.html         le <datalist> du champ « votre commune »
  aldente/index.html les coordonnées, pour poser les bulles sur la carte

Les blocs sont délimités par des marqueurs et réécrits en entier ; on ne les
modifie pas à la main. Relancer après toute mise à jour de lieux.json :

    python3 mesure/lieux.py
"""
import json
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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

    # ── index.html : les options du champ ────────────────────────────────
    options = '\n'.join('  <option value="%s">' % l['nom'] for l in lieux)
    remplace('index.html',
             '<!-- communes:début — engendré par mesure/lieux.py, ne pas modifier à la main -->',
             '<!-- communes:fin -->',
             options)

    # ── aldente/index.html : les coordonnées de la carte ─────────────────
    c = d['_centre']
    paires = []
    for l in lieux:
        paires.append('%s:[%s,%s]' % (json.dumps(l['nom'], ensure_ascii=False), l['lat'], l['lon']))
    corps, ligne = [], '    '
    for p in paires:
        if len(ligne) + len(p) > 104:
            corps.append(ligne.rstrip())
            ligne = '    '
        ligne += p + ','
    corps.append(ligne.rstrip().rstrip(','))
    js = ('  /* Coordonnées des localités, relevées sur OpenStreetMap (ODbL). */\n'
          '  var CENTRE = [%s, %s];\n'
          '  var LIEUX = {\n%s\n  };' % (c['lat'], c['lon'], '\n'.join(corps)))
    remplace('aldente/index.html',
             '  /* communes:début — engendré par mesure/lieux.py, ne pas modifier à la main */',
             '  /* communes:fin */',
             js)
    return 0


if __name__ == '__main__':
    sys.exit(main())
