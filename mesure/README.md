# Mesure de fréquentation — mise en service

Le tableau de bord vit à **`/aldente/`**. Il lit ses chiffres auprès d'un petit
service hébergé chez Cloudflare, qui reçoit les événements du site et n'en
conserve que des totaux.

Tant que ce service n'est pas en ligne, la page affiche un message d'attente et
propose `/aldente/?demo=1`, qui montre la mise en page avec des chiffres fictifs
clairement signalés. Utile pour la présentation aux gérants.

---

## Ce qui est mesuré, et ce qui ne l'est pas

| Enregistré | Jamais enregistré |
|---|---|
| Nombre de visites par jour | Qui a visité |
| Ville approximative, en total (« Liège : 34 ») | Adresse IP |
| Type d'appareil, en total | Navigateur, système, empreinte |
| Appels et itinéraires lancés, en nombre | Numéro appelé, identité |
| Intitulés des plats mis au panier, en nombre | Panier d'une personne donnée |

Une seule ligne en base par `(jour, type, clé)`, incrémentée. Aucun parcours
individuel ne peut en être reconstitué — ce qui est exactement ce que promet la
page de mentions légales, et ce que le contrat annonce à l'article 14.

Aucun cookie n'est posé : **le bandeau de consentement n'a pas à être modifié.**

---

## Installation (environ 15 minutes, une seule fois)

### 1. Un compte Cloudflare

Gratuit, sur [dash.cloudflare.com](https://dash.cloudflare.com). Aucune carte
bancaire. Les volumes d'un restaurant restent très loin des limites de l'offre
gratuite (100 000 requêtes par jour, 100 000 écritures en base).

### 2. Les outils

```bash
npm install -g wrangler
wrangler login
```

### 3. La base de données

```bash
wrangler d1 create pino-mesure
```

Reportez le `database_id` renvoyé dans `wrangler.toml`, puis créez la table :

```bash
wrangler d1 execute pino-mesure --remote --file=mesure/schema.sql
```

### 4. La clé du tableau de bord

Choisissez une phrase que les gérants retiendront et qui ne se devine pas.
Elle n'est jamais écrite dans le code :

```bash
wrangler secret put CLE
```

### 5. Mise en ligne

```bash
wrangler deploy
```

Wrangler affiche l'adresse du service, par exemple
`https://pino-mesure.vincent-buron.workers.dev`.

### 6. Brancher les deux bouts

Reportez cette adresse, **sans barre oblique finale**, à deux endroits :

- `aldente/index.html` → `var API = '';` en tête du script
- `index.html` → `var API = '';` dans le bloc « Mesure de fréquentation », en fin de fichier

Puis incrémentez `CACHE` dans `sw.js` et poussez sur `main`.

---

## Vérifier que tout fonctionne

1. Ouvrez le site en navigation privée, cliquez sur « Appeler », composez un panier.
2. Ouvrez `/aldente/`, entrez la clé : les compteurs doivent bouger (le jour
   courant est en heure de Bruxelles).
3. Contrôle direct en base :

```bash
wrangler d1 execute pino-mesure --remote \
  --command="SELECT jour, type, cle, n FROM compteur ORDER BY jour DESC, n DESC LIMIT 30"
```

---

## Points de vigilance

**Vos propres visites sont comptées.** Si vous ouvrez le site vingt fois par jour
pendant le développement, les chiffres du premier mois seront faussés. Purgez
avant de montrer la page aux gérants :

```bash
wrangler d1 execute pino-mesure --remote --command="DELETE FROM compteur WHERE jour <= '2026-09-30'"
```

**La ville dépend du réseau du visiteur.** Un abonné mobile peut être rattaché à
la ville où se trouve le relais de son opérateur, pas là où il se tient. Le
libellé « Non localisé » apparaît quand Cloudflare ne sait pas trancher.
À présenter aux gérants comme une tendance, jamais comme une adresse.

**La liste `ORIGINES` dans `wrangler.toml` est la serrure.** Seules les origines
qui y figurent peuvent écrire. Si le site déménage sur son propre domaine,
ajoutez-le, sinon la mesure s'arrête silencieusement.

**La clé passe en clair dans l'en-tête `X-Pino-Cle`.** C'est sans danger sur
HTTPS, mais cette clé protège des chiffres de fréquentation, pas un compte en
banque : ne la réutilisez nulle part ailleurs.
