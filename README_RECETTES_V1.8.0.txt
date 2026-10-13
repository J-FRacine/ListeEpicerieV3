Recettes V1.8.0 — Mesures, nutrition automatique et PDF

Base attendue
- Recettes V1.7.0
- Portail V1.5.0 conservé
- GitHub main vérifié au commit :
  6959e611d03775f93410ee70abaa1a223ea236ca

1. CONVERSION DES MESURES
- Nouveau bouton Mesures dans les actions d’une recette.
- Reconnaissance des fractions : 1/2, 2/3, 1 1/2, ½, etc.
- Poids directs : g, kg, oz, lb.
- Volumes : ml, L, tasse, c. à soupe, c. à table, c. à thé.
- Les volumes sont convertis avec la densité propre à l’ingrédient.
- Certaines unités utilisent un poids moyen : œuf, banane, oignon, ail, etc.
- L’utilisateur peut choisir/corriger l’aliment de référence et le poids.
- La mesure originale n’est jamais remplacée.
- Les conversions enregistrées apparaissent sous la forme ≈ X g.

2. GÉNÉRATEUR NUTRITIONNEL
- Le bouton Valeurs nutritives conserve la saisie manuelle.
- Nouveau bouton Calculer automatiquement.
- Le calcul utilise les grammes vérifiés et un catalogue générique par 100 g.
- Total de la recette et valeur par portion.
- Toujours marqué Estimation.
- Les ingrédients non reconnus ou sans quantité sont signalés et exclus,
  jamais inventés.
- Le catalogue contient une première série d’ingrédients courants et pourra
  être enrichi dans les prochaines versions.

3. IMPRESSION / PDF / COURRIEL
- Bouton PDF / courriel dans les actions de la recette.
- Même action disponible depuis Consulter.
- Options : photo, nutrition et grammes convertis.
- Le PDF est téléchargé et peut être imprimé avec la commande Imprimer
  de l’appareil.
- Préparer le courriel ouvre un message avec sujet et texte préremplis.
- Le navigateur ne permet pas d’attacher automatiquement le PDF : il doit
  être joint manuellement au message, comme dans Journal de pression.

DONNÉES ET BASE
- Les conversions sont stockées dans recipe_extra JSONB existant.
- Elles sont donc conservées avec les sauvegardes qui incluent déjà recipe_extra.
- Aucune nouvelle table ou colonne.
- Aucune migration PostgreSQL.
- Aucun SQL manuel.
- Aucune nouvelle dépendance : reportlab est déjà utilisé par JF Apps.

INSTALLATION
1. Extraire ce ZIP à la racine de ListeEpicerieV3-main.
2. Lancer INSTALLER_RECETTES_V1.8.0.bat.
3. Si tous les tests réussissent, publier le ZIP généré :
   A_PUBLIER_GITHUB_RECETTES_V1.8.0_MESURES_NUTRITION_PDF.zip

VALIDATION NAVIGATEUR CONSEILLÉE
- Ouvrir une recette avec 1 tasse de farine et vérifier la conversion ≈ g.
- Corriger manuellement un poids et enregistrer.
- Vérifier que Consulter affiche le poids sans remplacer la mesure originale.
- Calculer automatiquement la nutrition et vérifier la mention Estimation.
- Tester un ingrédient non reconnu : il doit être signalé comme non inclus.
- Générer un PDF avec et sans photo/nutrition.
- Préparer un courriel.

L’installateur compile et exécute les tests locaux, mais ne teste pas
PostgreSQL de production ni Canner.
