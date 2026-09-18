#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fabrique les données structurées de la carte (schema.org Menu) à partir du
site lui-même, et les injecte dans index.html entre deux repères.

Le site reste la source : la carte affichée et celle que lit Google sont
tirées du même texte, elles ne peuvent pas diverger. À relancer après toute
modification de la carte — la vérification du dépôt échoue sinon.

    python3 menu/balisage.py            écrit le balisage dans index.html
    python3 menu/balisage.py --verifie  ne touche à rien, signale l'écart
"""

import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extrait

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(RACINE, 'index.html')
SITE = 'https://pizzeriapino.be/'
DEBUT = '<!-- carte-structuree:début — engendré par menu/balisage.py, ne pas modifier à la main -->'
FIN = '<!-- carte-structuree:fin -->'


def prix(brut):
    """« 10,50 » → « 10.50 ». Rend None si ce n'est pas un montant."""
    m = re.fullmatch(r'(\d+)[,.](\d{2})', (brut or '').strip())
    return '{}.{}'.format(m.group(1), m.group(2)) if m else None


def plat(p):
    item = {'@type': 'MenuItem', 'name': p['nom']}
    if p['desc']:
        item['description'] = p['desc']
    montant = prix(p['prix'])
    if montant:
        item['offers'] = {'@type': 'Offer', 'price': montant, 'priceCurrency': 'EUR'}
    return item


def menu():
    c = extrait.carte()
    sections = []
    for s in c['sections']:
        # Un groupe sans titre tient directement dans la section ; les autres
        # deviennent des sous-sections, comme sur la carte imprimée.
        directs, sous = [], []
        for g in s['groupes']:
            plats = [plat(p) for p in g['plats']]
            if not plats:
                continue
            if g['titre']:
                sous.append({'@type': 'MenuSection', 'name': g['titre'], 'hasMenuItem': plats})
            else:
                directs.extend(plats)
        bloc = {'@type': 'MenuSection', 'name': s['titre']}
        if directs:
            bloc['hasMenuItem'] = directs
        if sous:
            bloc['hasMenuSection'] = sous
        sections.append(bloc)

    return {
        '@context': 'https://schema.org',
        '@type': 'Menu',
        '@id': SITE + '#menu',
        'name': 'Carte de la Pizzeria Pino',
        'inLanguage': 'fr-BE',
        'url': SITE + '#carte',
        'hasMenuSection': sections,
    }


def bloc_html(donnees):
    return (DEBUT + '\n<script type="application/ld+json">'
            + json.dumps(donnees, ensure_ascii=False, separators=(',', ':'))
            + '</script>\n' + FIN)


def compte(donnees):
    n = 0
    for s in donnees['hasMenuSection']:
        n += len(s.get('hasMenuItem', []))
        for sous in s.get('hasMenuSection', []):
            n += len(sous.get('hasMenuItem', []))
    return n


def main():
    verifie = '--verifie' in sys.argv
    page = io.open(PAGE, encoding='utf-8').read()
    donnees = menu()
    neuf = bloc_html(donnees)

    if DEBUT not in page:
        print('Repères absents de index.html : ajoutez-les une fois près du JSON-LD.')
        return 2

    actuel = page[page.index(DEBUT):page.index(FIN) + len(FIN)]
    if actuel == neuf:
        print('Balisage de la carte à jour : {} plats, {} sections.'
              .format(compte(donnees), len(donnees['hasMenuSection'])))
        return 0

    if verifie:
        print('Le balisage de la carte ne correspond plus au site.\n'
              'Relancez : python3 menu/balisage.py')
        return 1

    io.open(PAGE, 'w', encoding='utf-8').write(page.replace(actuel, neuf))
    print('Balisage réécrit : {} plats, {} sections.'
          .format(compte(donnees), len(donnees['hasMenuSection'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
