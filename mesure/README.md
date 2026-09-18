# Mesure de fréquentation — mise en service

Le tableau de bord vit à **`/aldente/`**. Il lit ses chiffres auprès d'une
fonction Edge hébergée sur **Supabase**, qui reçoit les événements du site et
n'en conserve que des totaux.

Tant que la fonction n'est pas déployée, la page affiche un message d'attente et
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

- `aldente/index.html` → `var API = '';` en tête du script
- `index.html` → `var API = '';` dans le bloc « Mesure de fréquentation », en fin de fichier

Puis incrémentez `CACHE` dans `sw.js` et poussez sur `main`.

---

## Vérifier que tout fonctionne

1. Ouvrez le site en navigation privée, cliquez sur « Appeler », composez un panier.
2. Ouvrez `/aldente/`, entrez la clé : les compteurs doivent bouger (le jour
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

**Le mot de passe passe en clair dans l'en-tête `X-Pino-Cle`.** C'est sans danger
sur HTTPS, mais il protège des chiffres de fréquentation, pas un compte en
banque : ne le réutilisez nulle part ailleurs.

**Si `ipwho.is` tombe**, la mesure continue et range la visite en « Non
localisé ». Le site du restaurant, lui, n'est jamais ralenti : la balise part en
arrière-plan et son échec est ignoré.
