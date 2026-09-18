# Mise en ligne sur pizzeriapino.be

Marche à suivre complète, dans l'ordre. Chaque étape suppose la précédente
terminée — l'ordre n'est pas un confort, c'est ce qui évite de casser quelque
chose au milieu.

Compter **une heure de manipulation**, étalée sur une demi-journée à cause des
temps de propagation.

---

## Étape 0 — Ce qui ne doit jamais être touché

Onze lignes de la zone DNS font tourner la messagerie. Les modifier coupe
`info@pizzeriapino.be`.

| Ligne | Rôle |
|---|---|
| `@ MX 1 mx1.ovh.net.` · `5 mx2` · `100 mxb` | acheminement du courrier |
| `@ SPF "v=spf1 include:mx.ovh.com ~all"` | autorise OVH à envoyer au nom du domaine |
| `ovhmo1697749-selector1._domainkey` et `-selector2` | signature DKIM — sans elle, les mails partent en indésirable |
| `mail` · `smtp` · `pop3` · `imp` · `squirrel` · `ox` | accès à cette messagerie |
| `@ NS dns19.ovh.net.` · `ns19.ovh.net.` | serveurs de la zone elle-même |

Les lignes `ftp`, `ftp2`, `jabber`, `sip`, `vpn`, `_xmpp-*`, `_sip._udp`
appartiennent à l'ancien hébergement mutualisé. Elles ne gênent pas. On en fera
le ménage **après** la résiliation, pas avant.

---

## Étape 1 — La zone DNS, chez OVH

*Noms de domaine → pizzeriapino.be → Zone DNS.*

**Créer huit entrées**, sous-domaine **laissé vide** :

Type `A` :

```
185.199.108.153
185.199.109.153
185.199.110.153
185.199.111.153
```

Type `AAAA` :

```
2606:50c0:8000::153
2606:50c0:8001::153
2606:50c0:8002::153
2606:50c0:8003::153
```

**Modifier une entrée** : `www` · CNAME · cible `cronobots.github.io.`
— avec le point final, OVH le réclame.

**Supprimer une entrée** : `@` · A · `213.186.33.3`, l'ancien site.

> Ne pas s'occuper du TTL. Il vaut six heures, donc certains visiteurs verront
> encore l'ancien site pendant quelques heures. Ce n'est pas grave : on remplace
> un site que personne ne consulte, et la messagerie, elle, ne bouge pas.

---

## Étape 2 — Attendre, et vérifier

```bash
nslookup pizzeriapino.be
```

Tant que la réponse est `213.186.33.3`, ne pas continuer. Il faut voir du
`185.199.x`. Vérification plus fiable sur **dnschecker.org** : taper
`pizzeriapino.be` et attendre du vert sur la plupart des points du globe.

Compter de quelques minutes à deux heures.

> Ne pas se fier à son propre navigateur : il garde lui aussi des réponses en
> mémoire et affichera l'ancien site plus longtemps que tout le monde.

---

## Étape 3 — GitHub Pages

Dépôt **PIZZAPINO** → *Settings* → *Pages* → **Custom domain** →
`pizzeriapino.be` → *Save*.

GitHub vérifie le domaine et crée tout seul un fichier `CNAME` à la racine du
dépôt. Il demande ensuite un certificat.

Quand la case **« Enforce HTTPS »** devient cliquable — quelques minutes,
parfois quelques heures — **la cocher**.

> Faire cette étape **avant** l'étape 2 rend le site inaccessible : l'adresse
> `cronobots.github.io/PIZZAPINO/` se met à rediriger vers un domaine qui
> affiche encore l'ancien site.

---

## Étape 4 — Les adresses dans le code

**Onze adresses absolues** pointent encore sur `cronobots.github.io/PIZZAPINO/` :
l'URL canonique, les balises de partage, l'image du partage, le plan du site,
les données structurées Google, `robots.txt` et `legal.html`.

Tant qu'elles ne sont pas migrées, Google voit deux sites identiques et n'en
indexe correctement aucun.

**Prévenir Claude dès que l'étape 3 est finie** — c'est un commit, pas une
manipulation.

---

## Étape 5 — La mesure de fréquentation

Détail complet dans [`mesure/README.md`](mesure/README.md). En résumé :

1. Coller `mesure/schema.sql` dans le *SQL Editor* de Supabase, projet
   **PIZZERIAPINO** → *Run*.
2. Déployer la fonction Edge :
   ```bash
   supabase link --project-ref <ref-du-projet>
   mkdir -p supabase/functions/mesure
   cp mesure/index.ts supabase/functions/mesure/index.ts
   supabase functions deploy mesure --no-verify-jwt
   ```
3. Les variables — **penser au nouveau domaine dans `ORIGINES`**, sinon la
   mesure s'arrête en silence :
   ```bash
   supabase secrets set CLE_TABLEAU="votre-phrase-de-passe"
   supabase secrets set ORIGINES="https://pizzeriapino.be,https://cronobots.github.io"
   ```
4. Reporter l'adresse `https://<ref>.supabase.co/functions/v1/mesure` dans les
   deux `var API = '';` — `index.html` et `aldente/index.html`.
5. Incrémenter `CACHE` dans `sw.js`, pousser sur `main`.

---

## Étape 6 — Contrôler que tout tient

| À vérifier | Comment |
|---|---|
| Le site répond en HTTPS | `https://pizzeriapino.be` — cadenas fermé |
| `www` redirige | `https://www.pizzeriapino.be` → doit arriver sur le site |
| L'ancienne adresse redirige | `cronobots.github.io/PIZZAPINO/` → doit basculer sur le nouveau domaine |
| **La messagerie vit toujours** | s'envoyer un message à `info@pizzeriapino.be` depuis une adresse extérieure |
| L'application s'installe | ouvrir sur téléphone → « Ajouter à l'écran d'accueil » |
| Le tableau de bord | `pizzeriapino.be/aldente/` → la clé est demandée, les chiffres montent |
| L'aperçu de partage | coller le lien dans WhatsApp → logo et phrase du hero |

---

## Étape 7 — Après la mise en ligne

**Google Search Console** — ajouter la propriété `pizzeriapino.be`, la vérifier
par un enregistrement TXT dans la zone OVH, et y déposer
`https://pizzeriapino.be/sitemap.xml`. C'est ce qui accélère la reprise en
compte du nouveau domaine.

**Fiche Google Business Profile** — remplacer l'ancienne adresse du site par
`https://pizzeriapino.be`. C'est le premier levier du référencement local : à ne
pas oublier.

**Aperçus en cache** — Facebook et WhatsApp gardent les anciens aperçus
plusieurs jours. Passer l'URL dans le *Sharing Debugger* de Facebook et cliquer
« Scrape Again ».

**DMARC** — le domaine n'en a aucun. Sans lui, n'importe qui peut envoyer des
courriels en se faisant passer pour la pizzeria. À poser une fois le reste
stabilisé.

**L'hébergement OVH** — `cluster015` continue d'être facturé alors qu'il ne sert
plus rien. ⚠️ **Avant de résilier, vérifier à quoi tient la messagerie** : chez
OVH, le MX Plan est souvent lié à la formule d'hébergement, et résilier l'un peut
tuer l'autre.

---

## Si quelque chose tourne mal

**Le site n'apparaît pas** — attendre. La propagation peut prendre plusieurs
heures. Vérifier sur dnschecker.org, jamais dans son propre navigateur.

**GitHub refuse le domaine** — le DNS ne pointe pas encore sur lui. Retour à
l'étape 2.

**« Enforce HTTPS » reste grisé** — le certificat n'est pas encore émis.
Patienter, puis retirer et remettre le domaine dans les réglages Pages.

**La messagerie ne répond plus** — vérifier immédiatement que les trois MX, le
SPF et les deux `_domainkey` sont intacts dans la zone. C'est le seul incident
réellement grave de toute la manœuvre.

**Tout revenir en arrière** — remettre `@ A 213.186.33.3`, remettre `www` sur
`pizzeriapino.be.`, retirer le domaine dans GitHub Pages. Le site repart sur
`cronobots.github.io/PIZZAPINO/`.
