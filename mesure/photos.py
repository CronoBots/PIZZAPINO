#!/usr/bin/env python3
"""
Donne un nom et une vignette aux images du site, pour le tableau de bord.

Deux choses s'y comptent par une clé courte, et le tableau de bord a besoin de
savoir ce que cette clé désigne :
  — les photos qu'on agrandit, comptées par la racine de leur fichier ;
  — les publications et reels du fil Instagram, comptés par leur code court.

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
# Les publications du fil Instagram : leur code court, leur libellé, leur image.
PUBLICATION = re.compile(
    r'<a\b[^>]*href="https?://(?:[a-z0-9-]+\.)*instagram\.com/(?:reel|reels|p|tv)/'
    r'([A-Za-z0-9_-]{5,20})[^"]*"[^>]*>(?:(?!</a>).)*?<img\b[^>]*\bsrc="([^"]+)"',
    re.I | re.S)
ETIQUETTE = re.compile(r'\baria-label="([^"]*)"', re.I)
CODE_OK = re.compile(r'^[A-Za-z0-9_-]{5,20}$')
TITRE_G = re.compile(r'\bdata-lb-title="([^"]*)"', re.I)
PHOTO = re.compile(r'\bdata-full="([^"]+)"')
LEGENDE = re.compile(r'<span class="cap">([^<]*)')
RACINE_OK = re.compile(r'^[a-z0-9][a-z0-9-]{0,39}$')


def cle_de(chemin):
    """« images/winter/w-07.jpg » → « w-07 », la clé telle qu'elle arrive en base."""
    base = chemin.rsplit('/', 1)[-1]
    return base.rsplit('.', 1)[0].lower()


def photos_par_cle(html):
    """({ racine : libellé lisible }, { racine : chemin du fichier })."""
    galeries = [(m.start(), m.group(1), (TITRE_G.search(m.group(0)) or [None, ''])[1])
                for m in GALERIE.finditer(html)]
    table = {}
    fichiers = {}
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
        fichiers.setdefault(cle, m.group(1))
    return table, fichiers


def pubs_par_code(html):
    """({ code court : libellé }, { code court : chemin de l'image }).

    Le code court est ce qui part du site : « DU5_qJLDO6m ». On ne compte pas
    « pub-1 », le nom du fichier : remplacer une vignette par un nouveau reel
    lèguerait alors au suivant les chiffres du précédent.
    """
    table, fichiers = {}, {}
    for m in PUBLICATION.finditer(html):
        code, image = m.group(1), m.group(2)
        if not CODE_OK.match(code):
            continue
        # L'intitulé du lien dit déjà ce que la publication montre.
        etiq = ETIQUETTE.search(m.group(0))
        libelle = entites.unescape(etiq.group(1)).strip() if etiq else ''
        libelle = re.sub(r'\s+sur Instagram$', '', libelle, flags=re.I) or ('Publication ' + code)
        table.setdefault(code, libelle)
        fichiers.setdefault(code, image)

    # Cinq reels s'appellent « Reel Pizzeria Pino » : dans un classement, ils
    # se confondraient en une seule ligne à l'œil. On numérote d'après le nom
    # de leur image, pour que deux passages du script donnent le même numéro.
    doublons = {}
    for code, libelle in table.items():
        doublons.setdefault(libelle, []).append(code)
    for libelle, codes in doublons.items():
        if len(codes) < 2:
            continue
        for i, code in enumerate(codes, 1):
            n = re.search(r'(\d+)(?=\.[a-z0-9]+$)', fichiers.get(code, ''))
            table[code] = '%s n° %s' % (libelle, n.group(1) if n else i)
    return table, fichiers


VIGNETTES = os.path.join('images', 'vignettes', 'stats')
COTE = 160          # rendu vers 40 px a l'ecran, net sur un ecran dense


def vignettes(sources):
    """Une vignette carrée par photo, pour le tableau de bord.

    Les photos de la page pèsent de vingt à cent kilo-octets : en afficher
    vingt-cinq dans un classement chargerait plusieurs mégaoctets pour des
    images de quarante pixels de côté. On en tire donc des vignettes à part.
    """
    try:
        from PIL import Image
    except ImportError:
        print('  Pillow absent : vignettes inchangées (pip install pillow)')
        return

    dossier = os.path.join(RACINE, VIGNETTES)
    os.makedirs(dossier, exist_ok=True)
    faites, sautees, manquantes = 0, 0, []

    for cle, source in sorted(sources.items()):
        entree = os.path.join(RACINE, source)
        if not os.path.exists(entree):
            manquantes.append(source)
            continue
        sortie = os.path.join(dossier, cle + '.webp')
        if os.path.exists(sortie) and os.path.getmtime(sortie) >= os.path.getmtime(entree):
            sautees += 1
            continue
        with Image.open(entree) as im:
            im = im.convert('RGB')
            # Carré pris au centre : un classement aligne mal des vignettes
            # de proportions différentes.
            c = min(im.size)
            g, h = (im.width - c) // 2, (im.height - c) // 2
            im = im.crop((g, h, g + c, h + c)).resize((COTE, COTE), Image.LANCZOS)
            im.save(sortie, 'WEBP', quality=72, method=6)
        faites += 1

    print('  vignettes : %d écrites, %d déjà à jour' % (faites, sautees))
    for m in manquantes:
        print('  ATTENTION : fichier introuvable, pas de vignette — %s' % m)


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
        html = f.read()
    table, fichiers = photos_par_cle(html)
    pubs, fichiers_pubs = pubs_par_code(html)

    if not table:
        print('aucune photo agrandissable trouvée — index.html a-t-il changé ?')
        return 1

    print('%d photos, %d publications' % (len(table), len(pubs)))
    tout = dict(fichiers)
    tout.update(fichiers_pubs)
    vignettes(tout)

    remplace('statistiques/index.html',
             '/* photos:début — engendré par mesure/photos.py, ne pas modifier à la main */',
             '/* photos:fin */',
             '  /* Racine du fichier → ce que la photo montre. La base ne retient que\n'
             '     la racine ; le nom lisible, lui, vit dans index.html. */\n'
             + bloc('PHOTOS', table))

    remplace('statistiques/index.html',
             '/* pubs:début — engendré par mesure/photos.py, ne pas modifier à la main */',
             '/* pubs:fin */',
             '  /* Code court Instagram → ce que la publication montre. */\n'
             + bloc('PUBS', pubs))
    return 0


def bloc(nom, table):
    """La table en JavaScript, repliée pour ne pas dépasser la marge."""
    paires = ['%s:%s' % (json.dumps(c, ensure_ascii=False), json.dumps(l, ensure_ascii=False))
              for c, l in table.items()]
    lignes, courante = [], '  var %s = {' % nom
    for p in paires:
        if len(courante) + len(p) + 1 > 96:
            lignes.append(courante)
            courante = '    '
        courante += p + ','
    lignes.append(courante.rstrip(',') + '};')
    return '\n'.join(lignes)


if __name__ == '__main__':
    sys.exit(main())
