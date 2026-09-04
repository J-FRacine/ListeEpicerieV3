# Installer et utiliser Codex pour JF Apps — Windows

Dernière mise à jour : 2026-09-04

## Installation recommandée

La méthode la plus simple est d'utiliser la nouvelle application de bureau ChatGPT, qui inclut maintenant **ChatGPT, Work et Codex** sur Windows.

### Étapes

1. Ouvre la page officielle de téléchargement :
   `https://chatgpt.com/download/`

2. Installe l'application ChatGPT pour Windows.
   Si Windows te redirige vers le Microsoft Store, installe l'application officielle OpenAI.

3. Ouvre l'application et connecte-toi avec le même compte ChatGPT que celui que tu utilises actuellement.

4. Dans le coin supérieur gauche de l'application, ouvre le sélecteur principal et choisis **Codex**.

5. Dans Codex, ouvre le dossier local de ton dépôt JF Apps.
   Le bon dossier est celui qui contient notamment :
   - `app.py`
   - `finances.py`
   - `finances_data.py`
   - `app_versions.py`
   - `manual.py`
   - les `finances_part_XX.pyfrag`
   - les `finances_data_part_XX.pyfrag`

6. Ajoute à la racine de ce dossier :
   - `AGENTS.md`
   - `PROJECT_STATUS.md`

7. Codex lira automatiquement `AGENTS.md` pour connaître les règles de travail du projet.

## Si tu n'as pas encore une copie locale propre du dépôt

Le plus simple est de cloner le dépôt avec GitHub Desktop, puis d'ouvrir ce dossier dans Codex.

Dépôt :
`J-FRacine/ListeEpicerieV3`

Si tu préfères continuer à télécharger le dépôt en ZIP depuis GitHub, Codex peut travailler dans ce dossier, mais GitHub Desktop est préférable pour suivre clairement les modifications et les commits.

## Premier message recommandé dans Codex

Tu peux commencer avec :

> Lis AGENTS.md et PROJECT_STATUS.md. Vérifie l'état actuel du dépôt sans modifier de fichier. Résume-moi les versions actuelles, la structure de Finances et les tests disponibles.

Ensuite, pour une vraie modification, utilise une fiche préparée avec ChatGPT.

## Exemple de tâche

> Finances V1.13.3. Pars exclusivement de la version actuelle du dépôt. Préserve les fonctionnalités existantes. Implémente la demande décrite ci-dessous. Mets à jour app_versions.py et manual.py. Compile tous les fichiers Python modifiés, reconstruis et compile les sources Finances à partir des fragments si nécessaire, exécute les tests pertinents disponibles, puis donne-moi un résumé et la liste des fichiers modifiés. Ne prétends pas avoir testé PostgreSQL ou Canner en production.

## Important

- Ne donne pas à Codex un ancien ZIP comme référence si le dépôt GitHub contient déjà une version plus récente.
- Laisse `main` comme référence stable et utilise les outils de worktree/branche proposés par Codex pour les changements importants.
- Relis toujours le résumé et le diff avant de déployer.
- Pour les changements sensibles de base de données, demande une migration automatisée et une stratégie de retour arrière.
