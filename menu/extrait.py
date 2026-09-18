#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lit la carte dans index.html et la rend sous forme structurée.

Le site est la source : le dépliant en est fabriqué, jamais l'inverse.
Les deux ne peuvent donc pas diverger.
"""

import html as H
import io
import json
import os
import re
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Les viandes suivent les pâtes : elles remplissent le premier feuillet,
# les pizzas occupent le second. C'est l'ordre du dépliant imprimé.
PANNEAUX = [('pates', 'Pâtes fraîches'), ('viandes', 'Viandes'),
            ('pizzas', 'Pizzas au feu de bois'), ('desserts', 'Desserts')]

JETON = re.compile(
    r'<div class="cat-title">(?P<titre>[^<]+)</div>'
    r'|<div class="dish">'
    r'<span class="name">(?P<nom>[^<]*)</span>'
    r'(?:<span class="dot"></span>)?'
    r'<span class="price">(?P<prix>[^<]*)</span>'
    r'(?:<small class="desc">(?P<desc>[^<]*)</small>)?')


def carte():
    html = io.open(os.path.join(RACINE, 'index.html'), encoding='utf-8').read()

    bornes = [(m.group(1), m.start()) for m in
              re.finditer(r'<div class="menu-panel[^"]*" id="([a-z]+)">', html)]
    fin_carte = html.index('<div class="center"', bornes[-1][1])
    coupes = {pid: (deb, bornes[i + 1][1] if i + 1 < len(bornes) else fin_carte)
              for i, (pid, deb) in enumerate(bornes)}

    sections = []
    for pid, libelle in PANNEAUX:
        deb, fin = coupes[pid]
        groupes, courant = [], {'titre': None, 'plats': []}
        for m in JETON.finditer(html[deb:fin]):
            if m.group('titre'):
                if courant['plats']:
                    groupes.append(courant)
                courant = {'titre': m.group('titre').strip(), 'plats': []}
            else:
                courant['plats'].append({
                    'nom': H.unescape(m.group('nom')).strip(),
                    'prix': H.unescape(m.group('prix')).strip(),
                    'desc': H.unescape(m.group('desc') or '').strip()})
        if courant['plats']:
            groupes.append(courant)
        sections.append({'id': pid, 'titre': libelle, 'groupes': groupes})

    # suppléments et pizza junior
    zone = html[fin_carte:html.index('</section>', fin_carte)]
    supps = [{'nom': H.unescape(m.group(1)).strip(), 'prix': H.unescape(m.group(2)).strip()}
             for m in re.finditer(r'<li[^>]*><span>([^<]+)</span><i></i><b>([^<]+)</b></li>', zone)]
    junior = re.search(r'<span class="sj-price">([^<]+)</span>', zone)

    return {'sections': sections, 'supplements': supps,
            'junior': junior.group(1).strip() if junior else None}


def main():
    c = carte()
    n = sum(len(g['plats']) for s in c['sections'] for g in s['groupes'])
    if '--json' in sys.argv:
        print(json.dumps(c, ensure_ascii=False, indent=1))
        return 0
    for s in c['sections']:
        print('\n%s' % s['titre'].upper())
        for g in s['groupes']:
            if g['titre']:
                print('  — %s —' % g['titre'])
            for p in g['plats']:
                print('    %-38s %7s  %s' % (p['nom'], p['prix'], p['desc'][:46]))
    print('\n%d plats · %d suppléments · junior %s'
          % (n, len(c['supplements']), c['junior']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
