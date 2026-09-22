#!/usr/bin/env python3
"""
Associe chaque photo agrandissable à un libellé lisible, pour le tableau de bord.

Ce qui part du site n'est pas le nom de la photo mais sa seule racine de
fichier : « etab-facade », « w-07 ». C'est volontaire — la fonction Edge
n'accepte que des minuscules, des chiffres et des traits d'union, donc rien
d'autre qu'une racine connue ne peut entrer en base.

Reste à retrouver, côté tableau de bord, ce que « w-07 » désigne. Ce script
lit index.html et en tire la correspondance, qu'il injecte dans
statistiques/index.html entre deux marqueurs.

Deux cas dans la page :
  — la galerie du restaurant, où chaque photo porte sa propre légende
    (« La façade », « La terrasse ») ;
  — la galerie d'une soirée, où les dix-neuf photos partagent un seul titre.
    On les numérote dans leur ordre d'affichage, sans quoi elles se
    confondraient toutes en une seule ligne du classement.

    python3 mesure/photos.py
"""
import html as entites
import json
import os
import re
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GALERIE = re.compile(r'<[a-z]+[^>]*\bdata-gallery="([^"]*)"[^>]*>', re.I)
TITRE_G = re.compile(r'\bdata-lb-title="([^"]*)"', re.I)
PHOTO = re.compile(r'\bdata-full="([^"]+)"')
LEGENDE = re.compile(r'<span class="cap">([^<]*)')
RACINE_OK = re.compile(r'^[a-z0-9][a-z0-9-]{0,39}$')


def cle_de(chemin):
    """« images/winter/w-07.jpg » → « w-07 », la clé telle qu'elle arrive en base."""
    base = chemin.rsplit('/', 1)[-1]
    return base.rsplit('.', 1)[0].lower()


def photos_par_cle(html):
    """{ racine du fichier : libellé lisible }, dans l'ordre de la page."""
    galeries = [(m.start(), m.group(1), (TITRE_G.search(m.group(0)) or [None, ''])[1])
                for m in GALERIE.finditer(html)]
    table = {}
    rang = {}

    trouvees = list(PHOTO.finditer(html))
    for i, m in enumerate(trouvees):
        fin = trouvees[i + 1].start() if i + 1 < len(trouvees) else len(html)

        # La galerie ouverte juste avant cette photo.
        nom_g, titre_g = '', ''
        for debut, nom, titre in galeries:
            if debut < m.start():
                nom_g, titre_g = nom, titre
            else:
                break

        rang[nom_g] = rang.get(nom_g, 0) + 1
        cle = cle_de(m.group(1))
        leg = LEGENDE.search(html, m.end(), fin)
        if leg and leg.group(1).strip():
            libelle = entites.unescape(leg.group(1)).strip()
        else:
            # Le numéro vient du nom du fichier quand il en porte un, et non du
            # rang d'affichage : réordonner la galerie renommerait sinon des
            # photos déjà comptées, et les chiffres d'hier changeraient de sujet.
            fin_chiffree = re.search(r'(\d+)$', cle)
            numero = int(fin_chiffree.group(1)) if fin_chiffree else rang[nom_g]
            libelle = '%s n° %d' % (entites.unescape(titre_g).strip() or nom_g, numero)

        if not RACINE_OK.match(cle):
            print('  ATTENTION : « %s » ne sera jamais compté — la fonction Edge '
                  'refuse cette racine.' % cle)
            continue
        table.setdefault(cle, libelle)
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
        table = photos_par_cle(f.read())

    if not table:
        print('aucune photo agrandissable trouvée — index.html a-t-il changé ?')
        return 1
    print('%d photos' % len(table))

    paires = ['%s:%s' % (json.dumps(c, ensure_ascii=False), json.dumps(l, ensure_ascii=False))
              for c, l in table.items()]
    lignes, courante = [], '  var PHOTOS = {'
    for p in paires:
        if len(courante) + len(p) + 1 > 96:
            lignes.append(courante)
            courante = '    '
        courante += p + ','
    lignes.append(courante.rstrip(',') + '};')

    remplace('statistiques/index.html',
             '/* photos:début — engendré par mesure/photos.py, ne pas modifier à la main */',
             '/* photos:fin */',
             '  /* Racine du fichier → ce que la photo montre. La base ne retient que\n'
             '     la racine ; le nom lisible, lui, vit dans index.html. */\n'
             + '\n'.join(lignes))
    return 0


if __name__ == '__main__':
    sys.exit(main())
