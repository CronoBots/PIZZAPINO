#!/usr/bin/env python3
"""
Engendre le contenu de /carte/ à partir de la carte d'index.html.

Pourquoi une page séparée : la carte est le contenu le plus riche du site —
cent vingt et un plats, avec leurs prix et leur composition — et elle vivait
dans un onglet de la page d'accueil, sans adresse à elle. Une page ne peut
porter qu'un seul titre : celui de l'accueil parle du restaurant, pas de la
carte ni des prix.

Pourquoi l'engendrer plutôt que la recopier : une carte recopiée diverge. Le
patron change un prix dans index.html, la page /carte/ garde l'ancien, et le
client arrive avec un tarif périmé. Ici la source reste unique — index.html —
et ce script réécrit le bloc entre deux marqueurs.

Un piège reproduit fidèlement, comme dans mesure/plats.py : un script de la
page ajoute « Pizza » devant les noms du panneau pizzas, et s'arrête à la
section « Pizza Bianca ». Le visiteur lit donc « Pizza Margherita » ; la page
/carte/ doit dire la même chose.

    python3 outils/carte.py              réécrit la page
    python3 outils/carte.py --verifie    dit seulement si elle a divergé
"""
import html as entites
import os
import re
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PANNEAU = re.compile(r'<div class="menu-panel[^"]*" id="([a-z]+)">')
MORCEAU = re.compile(
    r'<div class="cat-title">([^<]*)</div>'
    r'|<div class="dish">\s*<span class="name">([^<]+)</span>'
    r'.*?<span class="price">([^<]+)</span>'
    r'(?:\s*<small class="desc">([^<]*)</small>)?',
    re.S)
SUPPLEMENT = re.compile(r'<li( class="free")?><span>([^<]+)</span><i></i><b>([^<]+)</b></li>')
ONGLET = re.compile(r'<button class="tab[^"]*" data-tab="([a-z]+)">([^<]+)</button>')


def texte(v):
    return entites.unescape(v or '').strip()


def carte(html):
    """[(identifiant, titre d'onglet, [(sous-titre|None, [plats])])]."""
    titres = {m.group(1): texte(m.group(2)) for m in ONGLET.finditer(html)}
    ordre = [m.group(1) for m in ONGLET.finditer(html)]

    bornes = [(m.group(1), m.end()) for m in PANNEAU.finditer(html)]
    panneaux = {}
    for i, (cle, debut) in enumerate(bornes):
        fin = bornes[i + 1][1] if i + 1 < len(bornes) else html.index('</section>', debut)
        bloc = html[debut:fin]

        # Le préfixe « Pizza » cesse à la section Bianca : on cherche où.
        coupure = len(bloc)
        if cle == 'pizzas':
            for m in MORCEAU.finditer(bloc):
                if m.group(1) and 'bianca' in m.group(1).lower():
                    coupure = m.start()
                    break

        groupes, courant = [], (None, [])
        for m in MORCEAU.finditer(bloc):
            if m.group(1) is not None:
                if courant[1]:
                    groupes.append(courant)
                courant = (texte(m.group(1)), [])
                continue
            nom = texte(m.group(2))
            if cle == 'pizzas' and m.start() < coupure and not re.match(r'^pizza\b', nom, re.I):
                nom = 'Pizza ' + nom
            courant[1].append((nom, texte(m.group(3)), texte(m.group(4))))
        if courant[1]:
            groupes.append(courant)
        panneaux[cle] = groupes

    return [(c, titres.get(c, c), panneaux.get(c, [])) for c in ordre if panneaux.get(c)]


def supplements(html):
    bloc = html[html.index('<div class="supplements">'):]
    bloc = bloc[:bloc.index('</ul>')]
    return [(texte(m.group(2)), texte(m.group(3)), bool(m.group(1)))
            for m in SUPPLEMENT.finditer(bloc)]


def echappe(v):
    return (v.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def rendu(sections, supps):
    out = []
    for cle, titre, groupes in sections:
        out.append('  <section class="bloc" id="%s">' % cle)
        out.append('    <h2>%s</h2>' % echappe(titre))
        for sous_titre, plats in groupes:
            if sous_titre:
                out.append('    <h3>%s</h3>' % echappe(sous_titre))
            out.append('    <ul class="plats">')
            for nom, prix, desc in plats:
                ligne = ('      <li><span class="p-nom">%s</span>'
                         '<span class="p-prix">%s&nbsp;€</span>' % (echappe(nom), echappe(prix)))
                if desc:
                    ligne += '<span class="p-desc">%s</span>' % echappe(desc)
                out.append(ligne + '</li>')
            out.append('    </ul>')
        out.append('  </section>')

    out.append('  <section class="bloc" id="supplements">')
    out.append('    <h2>Suppléments</h2>')
    out.append('    <p class="note">La Pizza Junior (moins de 14 ans) est à −2,00&nbsp;€ '
               'du prix de la pizza choisie.</p>')
    out.append('    <ul class="plats supps">')
    for nom, prix, offert in supps:
        out.append('      <li%s><span class="p-nom">%s</span><span class="p-prix">%s</span></li>'
                   % (' class="offert"' if offert else '', echappe(nom),
                      echappe(prix) if offert else echappe(prix) + '&nbsp;€'))
    out.append('    </ul>')
    out.append('    <p class="note">Tarifs à emporter&nbsp;; les suppléments s’ajoutent au '
               'prix du plat.</p>')
    out.append('  </section>')
    return '\n'.join(out)


def remplace(chemin, debut, fin, contenu, verifie=False):
    """Écrit le bloc, ou dit seulement s'il a bougé quand on vérifie."""
    complet = os.path.join(RACINE, chemin)
    with open(complet, encoding='utf-8') as f:
        s = f.read()
    if debut not in s or fin not in s:
        print('  ignoré (marqueurs absents) : %s' % chemin)
        return 2
    i, j = s.index(debut), s.index(fin) + len(fin)
    neuf = s[:i] + debut + '\n' + contenu + '\n' + fin + s[j:]
    if neuf == s:
        print('  à jour : %s' % chemin)
        return 0
    if verifie:
        print('  LA PAGE /carte/ NE CORRESPOND PLUS À LA CARTE DU SITE.')
        print('  Relancez : python3 outils/carte.py')
        return 1
    with open(complet, 'w', encoding='utf-8') as f:
        f.write(neuf)
    print('  réécrit : %s' % chemin)
    return 0


def main():
    with open(os.path.join(RACINE, 'index.html'), encoding='utf-8') as f:
        html = f.read()

    sections = carte(html)
    supps = supplements(html)
    total = sum(len(p) for _, _, g in sections for _, p in g)
    print('%d plats en %d sections, %d suppléments'
          % (total, len(sections), len(supps)))
    for cle, titre, groupes in sections:
        print('  %-10s %s : %d' % (cle, titre, sum(len(p) for _, p in groupes)))

    if total < 100:
        print('ATTENTION : trop peu de plats, index.html a-t-il changé de forme ?')
        return 1

    return remplace('carte/index.html',
                    '<!-- carte:début — engendré par outils/carte.py, ne pas modifier à la main -->',
                    '<!-- carte:fin -->',
                    rendu(sections, supps),
                    verifie='--verifie' in sys.argv)


if __name__ == '__main__':
    sys.exit(main())
