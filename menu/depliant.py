#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fabrique le dépliant trois volets à partir de la carte du site.

    python3 menu/depliant.py            → menu/depliant-sombre.html + clair
    python3 menu/depliant.py --repartition "22,21,28,24,15"

Le site est la source. Le dépliant en découle, donc les prix imprimés et
les prix affichés ne peuvent pas diverger.
"""

import html as H
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extrait import carte, RACINE                                    # noqa: E402

SORTIE = os.path.join(RACINE, 'menu')

# Combien de plats sur chacun des cinq volets de carte (le sixième est la
# couverture). Ajusté par mesure : voir --repartition.
REPARTITION = [29, 24, 27, 28, 13]

THEMES = {
    'sombre': {
        'fond': '#14100D', 'panneau': '#191411', 'encre': '#F5EFE4',
        'attenue': '#B5AB99', 'discret': '#84796A', 'or': '#C69A4D',
        'or_clair': '#E9CE96', 'rouge': '#A8261D', 'rouge_clair': '#D9573F',
        'trait': 'rgba(245,239,228,.13)', 'voile': 'rgba(198,154,77,.07)',
        'pli': 'rgba(245,239,228,.16)',
    },
    'clair': {
        'fond': '#F5F0E6', 'panneau': '#FBF8F1', 'encre': '#1C1815',
        'attenue': '#4A423A', 'discret': '#8A7F72', 'or': '#9A7529',
        'or_clair': '#7E5F1E', 'rouge': '#A8261D', 'rouge_clair': '#8C1C14',
        'trait': 'rgba(28,24,21,.16)', 'voile': 'rgba(154,117,41,.08)',
        'pli': 'rgba(28,24,21,.2)',
    },
}


def e(t):
    """Le texte vient du HTML du site : on le ramène en clair, puis on l'échappe."""
    return H.escape(H.unescape(t or ''), quote=False)


# ── briques ──────────────────────────────────────────────────────────────

def ligne(p):
    d = ('<small>%s</small>' % e(p['desc'])) if p['desc'] else ''
    return ('<li><span class="n">%s</span><i></i><span class="p">%s</span>%s</li>'
            % (e(p['nom']), e(p['prix']), d))


def entete(titre, niveau='sec'):
    return '<h2 class="%s">%s</h2>' % (niveau, e(titre))


def bloc_plats(items):
    """Une suite de plats et d'intertitres, à plat."""
    out = []
    for it in items:
        suite = ' <span class="suite">suite</span>' if it.get('suite') else ''
        if it['type'] == 'section':
            out.append('<h2 class="sec">%s%s</h2>' % (e(it['titre']), suite))
        elif it['type'] == 'groupe':
            out.append('<h3 class="vedette">%s%s</h3>' % (e(it['titre']), suite))
        else:
            out.append(ligne(it['plat']))
    # les <li> consécutifs sont regroupés dans une <ul>
    rendu, dans = [], False
    for frag in out:
        if frag.startswith('<li'):
            if not dans:
                rendu.append('<ul class="plats">'); dans = True
        elif dans:
            rendu.append('</ul>'); dans = False
        rendu.append(frag)
    if dans:
        rendu.append('</ul>')
    return '\n'.join(rendu)


def couverture(c):
    return '''
    <div class="couv">
      <div class="couv-haut">
        <p class="sur">Restaurant italien · Nandrin</p>
        <h1>Pizzeria<br><em>Pino</em></h1>
        <span class="filet-or"></span>
        <p class="devise">Pizza, pasta, basta</p>
      </div>

      <div class="couv-mid">
        <p class="claim">Pizzas au feu de bois<br>Pâtes fraîches maison</p>
        <p class="emporter">Tarif à emporter</p>
      </div>

      <div class="horaires">
        <p class="h-t">Ouvert 7 jours sur 7</p>
        <div class="h-l"><span>Lundi au jeudi</span><b>12h–14h · 17h–21h30</b></div>
        <div class="h-l"><span>Vendredi à dimanche</span><b>12h–14h · 17h–22h</b></div>
      </div>

      <div class="couv-bas">
        <p class="adr">Route du Condroz 131<br>Centre commercial · 4550 Nandrin</p>
        <p class="tel">085 51 33 39</p>
        <p class="web">pizzeriapino.be</p>
      </div>
    </div>'''


def supplements(c):
    lis = ''.join(
        '<li class="%s"><span>%s</span><i></i><b>%s</b></li>'
        % ('offert' if 'ffert' in s['prix'] else '', e(s['nom']), e(s['prix']))
        for s in c['supplements'])
    return '''
      <div class="encart">
        <h3 class="vedette">Pizza Junior <span class="age">−14 ans</span></h3>
        <p class="junior">%s<span>à déduire du prix de la pizza choisie</span></p>
      </div>
      %s
      <ul class="supps">%s</ul>
      <p class="note">Les suppléments s’ajoutent au prix du plat.</p>''' % (
        e(c['junior'] or ''), entete('Suppléments'), lis)


# ── assemblage ───────────────────────────────────────────────────────────

def aplatit(c):
    """La carte entière, en une file de jetons prête à découper en volets."""
    file = []
    for s in c['sections']:
        file.append({'type': 'section', 'titre': s['titre']})
        for g in s['groupes']:
            if g['titre']:
                file.append({'type': 'groupe', 'titre': g['titre']})
            for p in g['plats']:
                file.append({'type': 'plat', 'plat': p})
    return file


def decoupe(file, repartition):
    """Découpe la file en volets, sans jamais laisser un titre en bas de volet."""
    volets, i = [], 0
    for n in repartition:
        pris, compte = [], 0
        while i < len(file) and compte < n:
            pris.append(file[i])
            if file[i]['type'] == 'plat':
                compte += 1
            i += 1
        # un intertitre en queue de volet part avec le volet suivant ; un
        # intertitre suivi de moins de trois plats aussi, sinon le lecteur
        # tourne la page et perd le titre en route
        while pris and pris[-1]['type'] != 'plat':
            i -= 1
            pris.pop()
        queue = 0
        for jeton in reversed(pris):
            if jeton['type'] == 'plat':
                queue += 1
            else:
                if queue < 3:
                    for _ in range(queue + 1):
                        i -= 1
                        pris.pop()
                break
        volets.append(pris)
    if i < len(file):
        volets[-1].extend(file[i:])

    # un volet qui reprend une liste commencée ailleurs en rappelle le titre :
    # sans ça, le lecteur découvre « Pizza Bufala » sans savoir de quoi il s'agit
    section = groupe = None
    for v in volets:
        if v and v[0]['type'] == 'plat':
            rappel = groupe or section
            if rappel:
                v.insert(0, dict(rappel, suite=True))
        for jeton in v:
            if jeton['type'] == 'section':
                section, groupe = jeton, None
            elif jeton['type'] == 'groupe':
                groupe = jeton
    return volets


def page(volets, pli=True):
    return ('<div class="page">%s</div>'
            % ''.join('<div class="volet">%s</div>' % v for v in volets))


def construis(theme, repartition):
    c = carte()
    volets = decoupe(aplatit(c), repartition)
    corps = [bloc_plats(v) for v in volets]
    corps[4] += supplements(c)

    p1 = page([corps[0], corps[1], couverture(c)])
    p2 = page([corps[2], corps[3], corps[4]])

    t = THEMES[theme]
    css = FEUILLE % t
    return ('<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8">'
            '<title>Carte — Pizzeria Pino</title><style>%s</style></head>'
            '<body class="%s">%s%s</body></html>' % (css, theme, p1, p2))


FEUILLE = '''
@font-face{font-family:'Fraunces';font-style:normal;font-weight:400 700;
  src:url('../fonts/fraunces-normal-400_700.woff2') format('woff2')}
@font-face{font-family:'Fraunces';font-style:italic;font-weight:400 600;
  src:url('../fonts/fraunces-italic-400_600.woff2') format('woff2')}
@font-face{font-family:'Oswald';font-style:normal;font-weight:400;
  src:url('../fonts/oswald-normal-400.woff2') format('woff2')}
@font-face{font-family:'Inter';font-style:normal;font-weight:400;
  src:url('../fonts/inter-normal-400.woff2') format('woff2')}

@page{size:A4 landscape;margin:0}
*{box-sizing:border-box;margin:0;padding:0}
html,body{-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important}
body{background:%(fond)s;color:%(encre)s;font-family:'Inter',sans-serif}

.page{width:297mm;height:210mm;display:grid;grid-template-columns:repeat(3,1fr);
  background:%(fond)s;overflow:hidden;position:relative;page-break-after:always}
.page:last-child{page-break-after:auto}
/* marques de pliage, discrètes */
.page::before,.page::after{content:"";position:absolute;top:0;bottom:0;width:0;
  border-left:.3pt dashed %(pli)s}
.page::before{left:99mm}.page::after{left:198mm}

.volet{padding:7mm 6mm 6mm;display:flex;flex-direction:column;min-width:0}

/* ── titres ── */
h2.sec{font-family:'Oswald',sans-serif;font-size:7.6pt;letter-spacing:.2em;
  text-transform:uppercase;color:%(or)s;margin:3.4mm 0 1.8mm;
  padding-bottom:1mm;border-bottom:.5pt solid %(or)s}
.volet > h2.sec:first-child,.volet > *:first-child h2.sec{margin-top:0}
h3.vedette{font-family:'Fraunces',serif;font-style:italic;font-weight:600;
  font-size:9pt;color:%(rouge_clair)s;margin:2.8mm 0 1.6mm;
  padding:1.2mm 2.2mm;background:%(voile)s;border-left:1.4pt solid %(rouge)s}
h3.vedette .age{font-family:'Inter',sans-serif;font-style:normal;font-size:6.6pt;
  color:%(discret)s;letter-spacing:.04em}
.suite{font-family:'Inter',sans-serif;font-style:italic;font-weight:400;
  font-size:5.6pt;letter-spacing:.06em;text-transform:none;color:%(discret)s;
  vertical-align:.4mm;margin-left:1.4mm}

/* ── plats ── */
ul.plats,ul.supps{list-style:none}
ul.plats li{display:grid;grid-template-columns:1fr auto;column-gap:1.6mm;
  align-items:baseline;margin-bottom:1mm;break-inside:avoid}
ul.plats li .n{font-family:'Oswald',sans-serif;font-size:6.6pt;letter-spacing:.035em;
  text-transform:uppercase;color:%(encre)s;line-height:1.12}
ul.plats li i{grid-column:1/2;display:none}
ul.plats li .p{font-family:'Fraunces',serif;font-weight:600;font-size:7.2pt;
  color:%(or_clair)s;font-variant-numeric:tabular-nums;white-space:nowrap}
ul.plats li small{grid-column:1/-1;font-size:5.3pt;line-height:1.2;color:%(discret)s;
  margin-top:.15mm;display:block}

/* ── suppléments ── */
ul.supps{columns:2;column-gap:5mm}
ul.supps li{display:grid;break-inside:avoid;grid-template-columns:auto 1fr auto;column-gap:1.4mm;
  align-items:baseline;margin-bottom:1mm;font-family:'Oswald',sans-serif;
  font-size:6.6pt;letter-spacing:.05em;text-transform:uppercase;color:%(attenue)s}
ul.supps li i{border-bottom:.4pt dotted %(trait)s;transform:translateY(-.8mm)}
ul.supps li b{font-family:'Fraunces',serif;font-weight:600;color:%(or_clair)s;
  font-variant-numeric:tabular-nums}
ul.supps li.offert b{color:%(rouge_clair)s}
.encart{margin:5mm 0 0}
.junior{font-family:'Fraunces',serif;font-weight:600;font-size:13pt;color:%(or_clair)s;
  display:flex;align-items:baseline;gap:2.4mm;margin-top:1mm}
.junior span{font-family:'Inter',sans-serif;font-weight:400;font-size:6.2pt;
  color:%(discret)s;line-height:1.3}
.note{font-size:6.2pt;color:%(discret)s;font-style:italic;margin-top:2.6mm}

/* ── couverture ── */
.couv{display:flex;flex-direction:column;justify-content:space-between;height:100%%;
  text-align:center;padding:2mm 0}
.sur{font-family:'Oswald',sans-serif;font-size:6.6pt;letter-spacing:.24em;
  text-transform:uppercase;color:%(or)s;margin-bottom:3.5mm}
.couv h1{font-family:'Fraunces',serif;font-weight:600;font-size:30pt;line-height:.98;
  letter-spacing:-.015em;color:%(encre)s}
.couv h1 em{font-style:italic;color:%(rouge_clair)s}
.filet-or{display:block;width:16mm;height:.8pt;background:%(or)s;margin:4mm auto 3mm}
.devise{font-family:'Fraunces',serif;font-style:italic;font-size:10.5pt;color:%(or_clair)s}
.claim{font-family:'Oswald',sans-serif;font-size:8.6pt;letter-spacing:.1em;
  text-transform:uppercase;line-height:1.7;color:%(attenue)s}
.emporter{font-family:'Oswald',sans-serif;font-size:10pt;letter-spacing:.18em;
  text-transform:uppercase;color:%(fond)s;background:%(rouge)s;
  padding:2.2mm 3mm;margin-top:4mm;border-radius:1mm}
.horaires{border-top:.5pt solid %(trait)s;border-bottom:.5pt solid %(trait)s;padding:4mm 0}
.h-t{font-family:'Oswald',sans-serif;font-size:6.6pt;letter-spacing:.2em;
  text-transform:uppercase;color:%(or)s;margin-bottom:3mm}
.h-l{display:flex;flex-direction:column;gap:.6mm;margin-bottom:2.6mm}
.h-l:last-child{margin-bottom:0}
.h-l span{font-family:'Fraunces',serif;font-style:italic;font-size:9pt;color:%(encre)s}
.h-l b{font-family:'Inter',sans-serif;font-weight:400;font-size:7.4pt;color:%(attenue)s;
  font-variant-numeric:tabular-nums}
.adr{font-size:7.4pt;line-height:1.5;color:%(attenue)s}
.tel{font-family:'Fraunces',serif;font-weight:600;font-size:17pt;color:%(or_clair)s;
  margin:2.5mm 0 1mm;font-variant-numeric:tabular-nums}
.web{font-family:'Oswald',sans-serif;font-size:7.4pt;letter-spacing:.14em;
  text-transform:uppercase;color:%(or)s}
'''


def main():
    rep = REPARTITION
    for a in sys.argv[1:]:
        if a.startswith('--repartition'):
            rep = [int(x) for x in sys.argv[sys.argv.index(a) + 1].split(',')]
    for theme in ('sombre', 'clair'):
        chemin = os.path.join(SORTIE, 'depliant-%s.html' % theme)
        io.open(chemin, 'w', encoding='utf-8').write(construis(theme, rep))
        print('écrit :', os.path.relpath(chemin, RACINE))
    print('répartition des volets :', rep)
    return 0


if __name__ == '__main__':
    sys.exit(main())
