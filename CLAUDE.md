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
