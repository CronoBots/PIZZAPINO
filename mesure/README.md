# Mesure de fréquentation — mise en service

Le tableau de bord vit à **`/statistiques/`**. Il lit ses chiffres auprès d'une
fonction Edge hébergée sur **Supabase**, qui reçoit les événements du site et
n'en conserve que des totaux.

Tant que la fonction n'est pas déployée, la page affiche un message d'attente et
propose `/statistiques/?demo=1`, qui montre la mise en page avec des chiffres fictifs
clairement signalés. Utile pour la présentation aux gérants.

---

## Ce qui est mesuré, et ce qui ne l'est pas

| Enregistré | Jamais enregistré |
|---|---|
| Nombre de visites du site par jour | Qui a visité |
| Ville approximative, en total (« Liège : 34 ») | Adresse IP |
| Type d'appareil, en total | Navigateur, système, empreinte |
| Heure de la visite, en total (« 19 h : 42 ») | L'horodatage d'une visite précise |
| Appels et itinéraires lancés, en nombre | Numéro appelé, identité |
| Intitulés des plats mis au panier, en nombre | Panier d'une personne donnée |
| Clics vers Instagram et Facebook, et d'où ils partent | L'adresse cliquée, le compte visé |
| Reels et publications ouverts, par code court | Les vues, les abonnés, ce qui se passe chez Meta |
| Photos agrandies, par racine de fichier | Qui a ouvert quelle photo |

**Une visite n'est pas une personne.** Sans cookie ni identifiant — c'est le
choix de conception — un même client qui revient le lendemain est recompté. Le
tableau de bord dit donc « visites du site », jamais « visiteurs uniques ».
Une visite = un chargement de la page.

**La ville est approximative, et la carte le dit.** Elle vient de l'adresse IP,
qui situe le point de sortie de l'opérateur, pas le client : avec 90 % de trafic
mobile, un habitant du Condroz ressort le plus souvent « Liège ». Le tableau de
bord la présente comme un bassin, jamais comme une adresse. Les coordonnées des
lieux viennent de `mesure/lieux.json` (relevé OpenStreetMap, licence ODbL) ;
après toute mise à jour de ce fichier, relancer `python3 mesure/lieux.py` pour
réécrire le bloc engendré dans `statistiques/index.html`.

**Trois blocs de `statistiques/index.html` sont engendrés**, entre marqueurs, et
ne se modifient pas à la main :

| Script | Ce qu'il écrit | À relancer quand |
|---|---|---|
| `python3 mesure/lieux.py` | coordonnées des localités, contour du pays | `mesure/lieux.json` change |
| `python3 mesure/plats.py` | plat → section de la carte | la carte change dans `index.html` |
| `python3 mesure/photos.py` | noms lisibles et vignettes des photos et des publications | une photo ou une publication est ajoutée, retirée ou renommée |

**La photo « la plus vue » n'existe pas** : en descendant la page, on les voit
toutes. Ce qui est compté, c'est la photo *agrandie* — un geste délibéré. Et ce
qui part du site n'est pas son nom mais la seule racine de son fichier
(`etab-facade`, `w-07`) : le collecteur n'accepte que des minuscules, des
chiffres et des traits d'union, donc aucun libellé libre ne peut entrer en base.
Le nom lisible, lui, ne quitte jamais le site. Le script en tire aussi des
vignettes de 160 px (`images/vignettes/stats/`) : sans elles, le classement
chargerait plusieurs mégaoctets pour des images de quarante pixels de côté.
Il a besoin de Pillow (`pip install pillow`) ; sans lui, il met à jour les noms
et laisse les vignettes en l'état.

**Les réseaux : ce que le site sait, et ce qu'il ne saura jamais.** Il compte
les départs — un clic sur « Suivre », sur un reel, sur le lien du bloc contact —
avec l'endroit d'où part le clic, écrit dans le lien lui-même (`data-res`).
Le vocabulaire est fermé des deux côtés : un libellé hors liste n'écrit rien.

Il ne compte pas, et ne comptera pas : les nouveaux abonnés, les vues d'un
reel, les mentions J'aime. Ces chiffres n'existent que chez Meta. Les obtenir
demanderait une application Meta, un compte professionnel relié, des jetons
d'accès renouvelés côté serveur et une validation par Meta — un chantier en
soi, sans rapport avec la mesure sans cookie faite ici. En attendant, ils se
lisent dans Instagram (Insights) et dans Meta Business Suite.

Un clic sur « Suivre » n'est donc pas un abonné de plus : c'est un visiteur
envoyé sur le compte.

**L'heure est déduite à l'arrivée, jamais transmise.** Le visiteur n'envoie ni
son horloge ni son fuseau : la fonction Edge lit l'heure de Bruxelles au moment
où elle écrit, et incrémente un compteur de plus — au même titre que la ville
ou l'appareil. Aucun horodatage individuel n'existe, donc aucun parcours n'en
sort. Le tableau de bord n'affiche l'heure que pour les visites.

**Les quatre mesures sont disponibles jour par jour.** Visites, appels,
itinéraires et paniers : la base les porte toutes depuis le premier jour, et
le tableau de bord laisse choisir celle que suit sa courbe. Un jour sans appel
n'a pas de ligne en base ; la page comble le trou par un zéro, sans quoi la
moyenne du mardi se calculerait sur les seuls mardis où le téléphone a sonné.

**Les robots sont écartés avant toute écriture.** Un `user-agent` de robot, de
sonde de surveillance ou d'aperçu de lien ne laisse aucune trace en base : sans
ce filtre, les totaux gonflent et les villes des centres de données (Bruxelles,
Zaventem) éclipsent les vraies communes.

Une seule ligne en base par `(jour, type, clé)`, incrémentée. Aucun parcours
individuel ne peut en être reconstitué — ce qui est exactement ce que promet la
page de mentions légales, et ce que le contrat annonce à l'article 14.

Aucun cookie n'est posé : **le bandeau de consentement n'a pas à être modifié.**

**La ville.** Elle vient d'une consultation de l'adresse IP chez `ipwho.is`,
faite **depuis la fonction Edge, pas depuis le navigateur du visiteur**. Le
visiteur n'ouvre donc aucune connexion vers un tiers, et son adresse n'est
jamais écrite en base. C'est ce qui permet de garder la mesure hors du bandeau
de consentement. Pour s'en passer complètement, mettre la variable `GEO` à `non`.

---

## Trois verrous

1. **La table est fermée.** RLS est actif et aucune policy n'est créée : ni
   lecture ni écriture pour le rôle `anon`. Les deux fonctions SQL ne sont
   accordées à personne d'autre qu'au rôle de service.
2. **La clé de service ne quitte jamais le serveur.** Elle vit dans la fonction
   Edge, jamais dans le JavaScript du site.
3. **Le mot de passe du tableau de bord est vérifié côté serveur**, en
   comparaison à durée constante, avant toute lecture.

> Si l'on exposait l'agrégation au rôle `anon`, quiconque ouvre le JavaScript du
> site pourrait lire les chiffres. C'est le piège à éviter.

---

## Installation (environ 15 minutes, une seule fois)

### 1. Le schéma

Supabase → projet **PIZZERIAPINO** → *SQL Editor* → *New query* → coller le
contenu de `mesure/schema.sql` → *Run*.

### 2. Les outils

```bash
npm install -g supabase
supabase login
supabase link --project-ref <ref-du-projet>
```

La référence du projet se lit dans l'URL du tableau de bord Supabase, ou dans
*Project Settings → General*.

### 3. La fonction Edge

```bash
mkdir -p supabase/functions/mesure
cp mesure/index.ts supabase/functions/mesure/index.ts
supabase functions deploy mesure --no-verify-jwt
```

Le `--no-verify-jwt` est indispensable : le site appelle la fonction sans jeton,
puisque c'est une balise posée par un visiteur anonyme. La protection vient de la
liste des origines et du mot de passe, pas d'un JWT.

### 4. Les variables

```bash
supabase secrets set CLE_TABLEAU="votre-phrase-de-passe"
supabase secrets set ORIGINES="https://cronobots.github.io,https://pizzeriapino.be"
supabase secrets set GEO="oui"
```

`SUPABASE_URL` et `SUPABASE_SERVICE_ROLE_KEY` sont fournies automatiquement, il
n'y a pas à les déclarer.

**Ajoutez le domaine définitif dans `ORIGINES` le jour de la bascule DNS**, sinon
la mesure s'arrêtera en silence.

### 5. Brancher les deux bouts

L'adresse de la fonction est
`https://<ref-du-projet>.supabase.co/functions/v1/mesure`.
Reportez-la, **sans barre oblique finale**, à deux endroits :

- `statistiques/index.html` → `var API = '';` en tête du script
- `index.html` → `var API = '';` dans le bloc « Mesure de fréquentation », en fin de fichier

Puis incrémentez `CACHE` dans `sw.js` et poussez sur `main`.

---

## Vérifier que tout fonctionne

1. Ouvrez le site en navigation privée, cliquez sur « Appeler », composez un panier.
2. Ouvrez `/statistiques/`, entrez la clé : les compteurs doivent bouger (le jour
   courant est en heure de Bruxelles).
3. Contrôle direct, depuis le *SQL Editor* :

```sql
select jour, type, cle, n from compteur order by jour desc, n desc limit 30;
```

---

## Points de vigilance

**Vos propres visites sont comptées.** Si vous ouvrez le site vingt fois par jour
pendant le développement, les chiffres du premier mois seront faussés. Purgez
avant de montrer la page aux gérants :

```sql
delete from compteur where jour <= '2026-09-30';
```

**La ville dépend du réseau du visiteur.** Un abonné mobile peut être rattaché à
la ville où se trouve le relais de son opérateur, pas là où il se tient. Le
libellé « Non localisé » apparaît quand le service ne sait pas trancher.
À présenter aux gérants comme une tendance, jamais comme une adresse.

**La clé doit être en ASCII simple** — lettres non accentuées, chiffres, tirets, points.
Un en-tête HTTP ne transporte pas les accents : une clé qui en contient arriverait
mutilée au serveur. La page refuse désormais ces clés avec un message clair plutôt
que de laisser l'accès échouer sans raison.

**La clé est remise sous forme de lien** : `https://pizzeriapino.be/statistiques/?k=VOTRE-CLE`.
La page la range en mémoire de session puis l'efface de la barre d'adresse. Les gérants
ajoutent ce lien à leur écran d'accueil et n'ont jamais rien à saisir.

**Le mot de passe passe en clair dans l'en-tête `X-Pino-Cle`.** C'est sans danger
sur HTTPS, mais il protège des chiffres de fréquentation, pas un compte en
banque : ne le réutilisez nulle part ailleurs.

**Si `ipwho.is` tombe**, la mesure continue et range la visite en « Non
localisé ». Le site du restaurant, lui, n'est jamais ralenti : la balise part en
arrière-plan et son échec est ignoré.
