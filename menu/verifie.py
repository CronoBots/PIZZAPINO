#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chien de garde du menu.

menu/menu.pdf est le menu officiel de la maison — un scan, sans couche texte.
On ne peut donc pas en recopier les prix automatiquement : la lecture
optique se trompe (« NEROME » pour NERONE, « 117,50 » pour 11,50). Écrire
un prix faux sur le site d'un restaurant est pire que ne rien écrire.

Ce script ne décide rien. Il constate que le PDF a changé depuis la
dernière synchronisation, rend les pages en images, et prépare un rapport
qu'un humain relit. La lecture optique n'y sert qu'à orienter le regard.

    python3 menu/verifie.py            → rapport sur la sortie standard
    python3 menu/verifie.py --scelle   → déclare le site synchronisé
"""

import hashlib
import io
import json
import os
import re
import subprocess
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Le scan a quitté la racine : servi par GitHub Pages, il y était une adresse
# publique — 567 Ko sans couche texte, illisible sur un téléphone, et Google
# l'affichait en lien sous le site. La carte se lit sur l'accueil, en texte :
# le scan n'a plus à être atteignable. Il reste ici, où le chien de garde le lit.
PDF     = os.path.join(RACINE, 'menu', 'menu.pdf')
SITE    = os.path.join(RACINE, 'index.html')
SCELLE  = os.path.join(RACINE, 'menu', 'synchro.json')
SORTIE  = os.path.join(RACINE, 'menu', 'apercu')

PRIX = re.compile(r'(\d{1,2})\s*[.,]\s*(\d{2})')


def empreinte(chemin):
    with open(chemin, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def plats_du_site():
    """Les plats affichés, lus dans le HTML : c'est la référence fiable."""
    html = io.open(SITE, encoding='utf-8').read()
    motif = re.compile(
        r'<div class="dish"><span class="name">([^<]+)</span>.*?'
        r'<span class="price">([^<]+)</span>', re.S)
    return [(m.group(1).strip(), m.group(2).strip()) for m in motif.finditer(html)]


def rend_et_lit():
    """Rend chaque page en image et en tente une lecture optique."""
    import pymupdf
    os.makedirs(SORTIE, exist_ok=True)
    doc = pymupdf.open(PDF)
    images, textes = [], []
    for i, page in enumerate(doc):
        chemin = os.path.join(SORTIE, 'menu-p%d.png' % (i + 1))
        page.get_pixmap(matrix=pymupdf.Matrix(4, 4)).save(chemin)
        images.append(chemin)
        try:
            textes.append(subprocess.run(
                ['tesseract', chemin, '-', '-l', 'fra', '--psm', '6'],
                capture_output=True, text=True, timeout=180).stdout)
        except Exception as e:
            textes.append('')
            print('  (lecture optique indisponible : %s)' % e, file=sys.stderr)
    return images, '\n'.join(textes)


def prix_normalises(texte):
    """Les montants repérés, ramenés à une forme comparable."""
    return sorted({'%d,%s' % (int(a), b) for a, b in PRIX.findall(texte)},
                  key=lambda p: float(p.replace(',', '.')))


def main():
    if not os.path.exists(PDF):
        print('menu/menu.pdf est absent.'); return 1

    actuel = empreinte(PDF)
    scelle = {}
    if os.path.exists(SCELLE):
        scelle = json.load(io.open(SCELLE, encoding='utf-8'))

    if '--scelle' in sys.argv:
        json.dump({'empreinte_menu_pdf': actuel,
                   'plats_sur_le_site': len(plats_du_site())},
                  io.open(SCELLE, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        io.open(SCELLE, 'a', encoding='utf-8').write('\n')
        print('Site déclaré synchronisé avec le menu actuel.')
        return 0

    if scelle.get('empreinte_menu_pdf') == actuel:
        print('Le site correspond au menu officiel en place. Rien à faire.')
        return 0

    site = plats_du_site()
    images, ocr = rend_et_lit()
    du_site = prix_normalises(' '.join(p for _, p in site))
    du_pdf  = prix_normalises(ocr)

    io.open(os.path.join(SORTIE, 'lecture-optique.txt'), 'w', encoding='utf-8').write(ocr)

    L = []
    L.append('## Le menu officiel a changé')
    L.append('')
    L.append('`menu/menu.pdf` ne correspond plus à la version avec laquelle le site '
             'a été synchronisé. **Le site n’a pas été modifié** : il faut le '
             'reprendre à la main.')
    L.append('')
    L.append('| | |')
    L.append('|---|---|')
    L.append('| Empreinte du PDF en place | `%s` |' % actuel[:16])
    L.append('| Empreinte de la dernière synchro | `%s` |'
             % (scelle.get('empreinte_menu_pdf', '— jamais synchronisé —')[:16]))
    L.append('| Plats actuellement sur le site | %d |' % len(site))
    L.append('')
    L.append('### À faire')
    L.append('')
    L.append('1. Ouvrir les images rendues (`menu/apercu/`) et les comparer au site.')
    L.append('2. Corriger `index.html` : noms, descriptions, prix.')
    L.append('3. Régénérer le PDF téléchargeable si les prix ont bougé.')
    L.append('4. Lancer `python3 menu/verifie.py --scelle` et pousser.')
    L.append('')
    L.append('### Piste, à ne pas prendre pour argent comptant')
    L.append('')
    L.append('La lecture optique du menu imprimé est approximative : elle '
             'confond les caractères et les points de conduite. Ce qui suit '
             'oriente le regard, **rien de plus**.')
    L.append('')

    absents = [p for p in du_pdf if p not in du_site]
    disparus = [p for p in du_site if p not in du_pdf]
    L.append('- Montants lus dans le PDF et absents du site : %s'
             % (', '.join(absents) if absents else '_aucun_'))
    L.append('- Montants présents sur le site et non retrouvés dans le PDF : %s'
             % (', '.join(disparus) if disparus else '_aucun_'))
    L.append('')
    L.append('Le texte brut de la lecture optique est dans '
             '`menu/apercu/lecture-optique.txt`.')

    rapport = '\n'.join(L)
    print(rapport)

    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write('desynchronise=true\n')
        io.open(os.path.join(SORTIE, 'rapport.md'), 'w', encoding='utf-8').write(rapport)
    return 0


if __name__ == '__main__':
    sys.exit(main())
