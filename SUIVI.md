# Suivi — Pizzeria Pino

Point d'étape pour reprendre le travail d'une session à l'autre. Dernière mise à
jour : 16 octobre 2026.

## En ligne et vérifié

- **Site** : pizzeriapino.be. Crédit « Réalisation : UPL⏻ADED » en pied de page.
- **Fonction `mesure`** (Supabase) : version **39**. Elle est déployée par un point
  d'entrée d'une ligne qui importe `mesure/index.ts` au commit `c0e02a9`
  (voir `mesure/README.md`). Avant tout nouveau déploiement, vérifier que la
  version en ligne correspond au dépôt.
- **Avis Google** : liste **figée** sur les 12 avis du 24/09 (`AVIS_FIGES`, actif par
  défaut). Seuls la note et le nombre d'avis se mettent à jour. Copie de secours :
  table `cache_avis`, clé `copie_2026-09-30`.
- **Instagram** : lu par Meta depuis le 13/10. Le compte pino.nandrin est relié à
  la page Facebook, et la clé de page `FB_JETON` contient `instagram_basic`.
- **Facebook** : lu par Meta, même clé.
- **Provenance des visites** : les liens publiés portent `?utm_source=instagram`,
  `facebook` ou `google`. Le marqueur est retiré de l'adresse dès la lecture.
- **Mobile** : bouton « Installer l'application » en bas de page. Le bandeau
  d'installation, lui, ne s'affiche jamais en mode app.
- **Ordinateur** : aucune proposition d'installation. Le manifeste n'est chargé que
  sur les écrans tactiles ou de 760 px de large au plus.

## À faire / échéances

- **Vers le 30/12/2026** : refaire la clé de page Meta (`FB_JETON`). Meta demande
  de reconfirmer l'accès aux données tous les 90 jours.
- **Réponses automatiques aux avis** :
  1. obtenir l'accès Google Business Profile, puis renseigner `GOOGLE_CLIENT_ID`,
     `GOOGLE_CLIENT_SECRET` et `GOOGLE_REFRESH_TOKEN` ;
  2. créer la clé `ANTHROPIC_API_KEY` ;
  3. ensuite seulement, écrire le module. Fonctionnement prévu : publication
     immédiate pour les avis de 4 et 5 étoiles ; pour ceux de 1 à 3 étoiles,
     publication après 24 h, modifiable ou annulable dans l'espace gérant.
- **Photos officielles** : en attente du patron, à mettre en ligne dès réception.
- **Lever le gel des avis** dès qu'une meilleure source existe (`AVIS_FIGES=non`).

## Proposition commerciale

Tenue hors de ce dépôt, qui est public et publié tel quel sur pizzeriapino.be.
La dernière version (8 pages) a été envoyée dans la conversation du 15/10/2026.
