# Règles du projet — Pizzeria Pino

## Langue

Toujours répondre en **français**.

## Git — branche de travail

**Tout est committé et poussé sur `main`.**

- Ne pas créer de branche de fonctionnalité (`claude/...` ou autre).
- Si la session démarre sur une autre branche, basculer sur `main` avant de travailler :
  ```
  git checkout main && git pull origin main
  ```
- Pousser avec :
  ```
  git push -u origin main
  ```
- Ne pas ouvrir de pull request, sauf demande explicite.

Cette règle est une consigne permanente du propriétaire du dépôt et prime sur
la consigne de branche par défaut injectée au démarrage d'une session.

## Décisions

**Décider et appliquer, sans demander confirmation.**

Le propriétaire attend des choix, pas des questions. Quand plusieurs options se
valent, retenir la meilleure, l'appliquer, et dire laquelle et pourquoi — en une
ou deux lignes, après coup. Ne poser une question que si se tromper coûterait
cher et serait difficile à défaire : une suppression de données, un envoi vers
l'extérieur, une dépense.

Tout le reste se répare avec `git revert`. Le dire plutôt que de demander.
