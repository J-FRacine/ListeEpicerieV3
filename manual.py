from nicegui import ui

from auth import get_current_user
from onboarding import organization_diagram


MANUAL_SECTIONS = [
    {
        "title": "Premiers pas",
        "icon": "rocket_launch",
        "caption": "Connexion, portail et installation",
        "keywords": (
            "connexion portail pwa installation écran accueil "
            "déconnexion démarrage"
        ),
        "content": """
### Se connecter

1. Ouvrez **JF Apps** dans le navigateur ou depuis son icône installée.
2. Entrez votre adresse courriel et votre mot de passe.
3. Après la connexion, le **Portail** présente les applications et les outils auxquels vous avez accès.

### Première connexion : commencez par créer votre famille

Une **famille** est l’espace où sont conservés vos items, besoins, magasins, catégories, listes modèles et recettes. Même lorsque vous utilisez l’application seul, vous devez obligatoirement créer une famille avant de commencer.

Depuis le Portail :

1. ouvrez **Commencer ici** pour voir le parcours visuel;
2. utilisez **Créer ma famille**;
3. ajoutez ensuite vos magasins et vos catégories;
4. créez enfin vos premiers items.

La page **Commencer ici** indique automatiquement les étapes déjà terminées.

### Repères visuels dans Commencer ici

La page **Commencer ici** contient aussi un guide visuel rapide des principaux boutons :

- **Items** : le catalogue de base;
- **Besoins** : la liste active d’achats;
- **Catégories** : l’organisation des catégories et des magasins;
- **Portail** : le retour à l’accueil général;
- **Planification** : les listes modèles, les recettes et la bibliothèque partagée;
- **Activité et corbeille** : l’historique récent et les suppressions récupérables;
- **Données** : importation, exportation et sauvegarde;
- **Manuel** : l’aide détaillée.

Ce repère est conçu pour qu’un nouvel utilisateur comprenne rapidement où cliquer, sans devoir fouiller dans toute l’application.

### Installer JF Apps sur un appareil

- Dans le Portail, utilisez **Installer JF Apps**.
- Sur Android et Chrome, acceptez l'installation proposée.
- Sur iPhone ou iPad, ouvrez le site dans Safari, puis utilisez **Partager → Sur l'écran d'accueil**.
- L'application a besoin d'une connexion Internet pour consulter et modifier les données partagées.

### Se déconnecter

Utilisez l'icône de déconnexion située dans l'en-tête du Portail ou de certaines pages administratives.
""",
    },
    {
        "title": "Portail et navigation",
        "icon": "apps",
        "caption": "En-tête commun et menus des applications",
        "keywords": (
            "portail navigation applications en-tête commun logo "
            "commentaires aide compte versions déconnexion onglets"
        ),
        "content": """
### Une navigation commune dans tout JF Apps

Le Portail et toutes les applications utilisent maintenant le même en-tête.

Il présente toujours :

- le logo JF Apps;
- le nom de la page ou de l’application;
- sa version lorsqu’elle est définie;
- un bouton **Portail**;
- un accès aux **Commentaires**;
- un accès au **Manuel**;
- un accès à **Mon compte**;
- un menu pour les nouveautés, l’installation de la PWA et la déconnexion.

Le logo et le bouton **Portail** ramènent tous deux au Portail principal.

Sur téléphone, l’en-tête est volontairement réduit à :

- le logo;
- le nom de l’application;
- sa version;
- le bouton **Portail**;
- un menu **Plus**.

Le menu Plus contient Commentaires, Aide, Mon compte, Nouveautés, Installer JF Apps et Déconnexion. Un indicateur peut signaler les commentaires non lus.

### Applications

La grille **Applications** du Portail contient :

- Liste d’épicerie;
- Journal de pression;
- Finances;
- Personnages JDR.

Chaque carte affiche sa version actuelle.

### Menus internes

L’en-tête commun sert à se déplacer dans tout JF Apps. Les onglets placés sous cet en-tête servent uniquement à naviguer à l’intérieur de l’application ouverte.

Dans **Finances**, les onglets donnent notamment accès au Tableau, à la Saisie, à l’Historique, aux Récurrences, aux Objectifs, à la Conciliation, à l’Organisation et à l’exportation.

Dans le **Journal de pression**, ils donnent accès à la Saisie, à l’Historique, au Rapport PDF et aux Rappels.

Dans **Personnages JDR**, ils donnent accès aux différentes sections de la feuille.

### Liste d’épicerie

La liste d’épicerie conserve une barre inférieure sur une seule ligne pour les actions quotidiennes :

- **Items**;
- **Besoins**;
- **Catégories** lorsque cette fonction est active, ou **Magasins** lorsqu’elle est désactivée.

Le bouton Portail a été retiré de cette barre parce qu’il est déjà disponible dans l’en-tête commun.

Sous l’en-tête commun, une petite barre d’outils donne accès à :

- **Planification** : listes modèles, recettes et bibliothèque;
- **Activité** : historique et corbeille;
- **Données** : importation, exportation et sauvegarde.

Le mode **Courses** conserve son écran simplifié, mais l’en-tête commun et le bouton Portail restent visibles.

### Logo, favicon et PWA

Le monogramme du logo JF Apps est utilisé comme :

- favicon dans l’onglet du navigateur;
- icône de la PWA;
- icône sur l’écran d’accueil;
- repère visuel dans l’en-tête commun.

Après une mise à jour, un rechargement complet du navigateur ou une réouverture de la PWA peut être nécessaire pour voir la nouvelle icône.
""",
    },
    {
        "title": "Finances — V1.4.0",
        "icon": "account_balance_wallet",
        "caption": "Dépenses, prévisions mensuelles et conciliation",
        "keywords": (
            "finances dépenses revenus récurrences catégories "
            "sous-catégories étiquettes objectifs report csv json "
            "paiement conciliation carte crédit KPI relevé "
            "solde prévu cumulatif séance historique ajustement "
            "postdaté à venir total prévu projection"
        ),
        "content": """
### Objectif de la V1

La V1 de **Finances** sert au suivi manuel des dépenses variables et des revenus. Elle ne constitue pas encore une comptabilité complète.

Les comptes bancaires, rapprochements comptables, transferts et écritures comptables sont prévus seulement pour une version future, probablement V3 ou V4. Les modes de paiement et la conciliation de la V1 préparent cette évolution sans imposer une comptabilité complète.

### Confidentialité

Toutes les données financières sont strictement privées à l’utilisateur connecté. Elles ne sont jamais partagées avec une famille ou un autre compte.

### Saisie rapide

La saisie permet d’enregistrer :

- une dépense ou un revenu;
- la date;
- le montant;
- une description;
- une catégorie ou sous-catégorie;
- plusieurs étiquettes;
- un mode de paiement;
- une note facultative;
- un statut confirmé ou prévu;
- un statut de conciliation.

Les champs principaux sont compacts pour faciliter l’utilisation sur téléphone.

### Catégories, sous-catégories et étiquettes

Une transaction peut avoir une catégorie ou une sous-catégorie, ainsi que plusieurs étiquettes.

Une même dépense peut compter dans plusieurs objectifs par étiquette. Les objectifs par étiquette ne doivent donc pas être additionnés pour calculer le total général.

### Modes de paiement

L’onglet **Organisation** contient une section **Modes de paiement**.

Les valeurs initiales sont :

- **MC Canadian Tire**;
- **MC PC**;
- **Visa Desjardins**;
- **Direct**.

L’utilisateur peut ajouter, renommer, désactiver et réordonner ses propres modes de paiement.

Pour chaque mode, il peut aussi préciser :

- le type : carte de crédit, compte bancaire, argent comptant ou autre;
- le jour habituel de fermeture du relevé;
- le jour habituel de paiement;
- un solde initial ou ajustement;
- la date de référence de cet ajustement;
- une note.

Le solde initial reste à concilier jusqu’à son inclusion dans une séance de conciliation.

Une transaction utilise un seul mode de paiement. Une transaction récurrente peut mémoriser son mode de paiement par défaut.

### Tableau mensuel : réalisé et à venir

Le Tableau distingue maintenant trois niveaux pour le mois affiché :

- **Réalisé** : transactions confirmées dont la date est atteinte;
- **À venir** : transactions prévues, postdatées ou issues d’une récurrence future;
- **Total prévu** : Réalisé + À venir.

Les récurrences actives sont projetées jusqu’à la fin du mois affiché sans créer immédiatement de transactions confirmées. Un revenu récurrent futur apparaît donc dans les prévisions dès qu’il appartient au mois consulté.

La section **Transactions à venir** affiche séparément :

- les dépenses prévues;
- les revenus prévus;
- leur effet net;
- la date;
- la description;
- le mode de paiement;
- l’indication **Récurrence projetée** ou **À confirmer**.

Les KPI par catégorie et par étiquette utilisent les colonnes :

- Réalisé;
- À venir;
- Total prévu.

Les dépenses et les revenus sont présentés dans des blocs distincts. Les noms trop longs sont tronqués, mais le nom complet demeure disponible au survol.

Une transaction portant plusieurs étiquettes peut apparaître dans plusieurs lignes. Les montants par étiquette ne doivent pas être additionnés pour obtenir le total général.

### Solde prévu cumulatif

Le **Tableau** affiche un solde prévu pour chaque mode de paiement.

Ce calcul ne recommence jamais à zéro au début d’un mois. Il traverse les mois jusqu’à ce que les transactions soient conciliées.

Le solde confirmé non concilié est calculé ainsi :

- dépenses confirmées non conciliées;
- moins les revenus, remboursements et crédits confirmés non conciliés;
- plus l’ajustement initial non concilié.

Les transactions prévues sont présentées séparément et ajoutées au **solde prévu**.

### Conciliation par relevé

L’onglet **Conciliation** permet de choisir un mode de paiement et d’afficher toutes ses transactions confirmées non conciliées, même lorsqu’elles proviennent de mois différents.

L’utilisateur peut :

- cocher une ou plusieurs transactions;
- tout sélectionner ou tout désélectionner;
- inscrire la date et le solde du relevé;
- inscrire la date de paiement;
- inscrire la date réelle de conciliation;
- inclure l’ajustement initial;
- voir le total sélectionné;
- voir le solde non concilié restant;
- voir la différence avec le solde du relevé;
- finaliser la sélection en une seule opération.

Une différence non nulle produit un avertissement, mais peut être conservée dans l’historique après confirmation.

Dès qu’une transaction est conciliée, elle cesse immédiatement de faire partie du solde confirmé non concilié.

### Historique des conciliations

Chaque séance conserve :

- le mode de paiement;
- la date et le solde du relevé;
- la date de paiement;
- la date de conciliation;
- les transactions sélectionnées;
- le total concilié;
- la différence;
- la note;
- l’ajustement initial, lorsqu’il a été inclus.

Une séance complète peut être annulée. Il est aussi possible de retirer une seule transaction d’une séance. La transaction redevient alors **À concilier** et retourne immédiatement dans le solde prévu.

Une transaction conciliée doit être retirée de sa conciliation avant de pouvoir être modifiée ou supprimée.

### Attribution en lot

L’écran **Conciliation** contient une section pour les transactions confirmées sans mode de paiement.

Plusieurs transactions peuvent être cochées et recevoir le même mode de paiement en une seule opération.

### Transactions récurrentes

Une dépense ou un revenu récurrent peut être configuré en jours, semaines, mois ou années.

Deux modes sont disponibles :

- **À confirmer** : l’occurrence devient une transaction prévue;
- **Création automatique** : l’occurrence est immédiatement confirmée.

La récurrence peut aussi mémoriser une catégorie, des étiquettes et un mode de paiement par défaut.

### Objectifs mensuels

Un objectif peut viser une catégorie, une sous-catégorie ou une étiquette.

Chaque objectif possède une politique de report :

- aucun report;
- report du montant inutilisé;
- report du dépassement;
- report des deux.

Un plafond de report facultatif peut être défini. Les mois déjà créés conservent leur montant de base et leur politique même si l’objectif est modifié plus tard.

### Tableau de bord

Le tableau de bord affiche :

- les dépenses;
- les revenus;
- la différence;
- les transactions prévues;
- la progression des objectifs;
- des KPI mensuels par catégorie;
- des KPI mensuels par étiquette;
- les soldes prévus cumulatifs par mode de paiement;
- la date de la plus ancienne transaction non conciliée;
- la date de la dernière séance de conciliation.

Les montants sont alignés à droite afin de faciliter la comparaison visuelle.

### Historique compact

L’historique regroupe les transactions par date.

Sur grand écran, les dépenses apparaissent dans la colonne de gauche et les revenus dans la colonne de droite. Sur téléphone, les deux sections sont empilées afin de préserver la lisibilité.

Tous les montants sont alignés à droite. Les descriptions, catégories, étiquettes et modes de paiement restent alignés à gauche.

Les filtres permettent de chercher par :

- dates;
- type;
- statut de transaction;
- catégorie;
- étiquette;
- mode de paiement;
- statut de conciliation;
- texte.

### Importer

L’onglet **Exporter** contient aussi la zone d’importation. Les formats reconnus sont :

- le CSV original de Spendee;
- le CSV exporté par JF Apps;
- le JSON exporté par JF Apps.

Avant l’importation, l’application présente le nombre de transactions valides, les transactions déjà importées, les doublons possibles, les catégories, les étiquettes et les modes de paiement détectés.

Les catégories, étiquettes et modes de paiement absents sont créés automatiquement.

Pour les exports Spendee contenant un horodatage UTC, la date est convertie selon le fuseau **America/Toronto**, adapté au Québec.

### Exporter

L’onglet **Exporter** produit un fichier CSV pour Excel et un fichier JSON complet de sécurité.

Les exportations contiennent maintenant :

- le mode de paiement;
- le statut de conciliation;
- la date de conciliation;
- la source et la clé d’importation.

### Versions

La version de l’application apparaît près de son nom. Le Portail contient aussi une page **Nouveautés et versions**.
""",
    },
    {
        "title": "Journal de pression",
        "icon": "monitor_heart",
        "caption": "Saisir, consulter et imprimer les mesures",
        "keywords": (
            "pression artérielle systolique diastolique pouls "
            "date heure appareil privé note historique pdf rapport "
            "aucune donnée courriel"
        ),
        "content": """
### Données privées

Le **Journal de pression** appartient uniquement à l’utilisateur connecté. Les mesures ne sont jamais partagées avec une famille ni avec un autre compte.

### Ajouter une mesure

Dans l’onglet **Saisie** :

1. la date et l’heure de l’appareil sont proposées automatiquement;
2. vérifiez-les ou modifiez-les au besoin;
3. inscrivez la pression systolique, la pression diastolique et le pouls;
4. ajoutez éventuellement une note;
5. utilisez **Enregistrer**.

Il est possible d’enregistrer plus de deux mesures dans une même journée. La phase 1 ne calcule aucune moyenne et ne présente aucun graphique.

### Horaires et rappel sur le Portail

L’onglet **Rappel** permet de définir :

- une date de début;
- une date de fin;
- l’activation ou la désactivation de l’avis;
- une ou plusieurs prises quotidiennes;
- un nom et une plage horaire pour chaque prise.

Exemple :

- **Matin** : de 6 h à 11 h;
- **Soir** : de 17 h à 22 h.

Les heures sont choisies par l’utilisateur. Les plages ne peuvent pas se chevaucher et doivent se terminer dans la même journée.

Les plages sont seulement des **repères pour les avis**. Toute mesure enregistrée pendant la journée compte comme une prise complétée, même si elle est faite avant ou après la plage suggérée.

Les mesures de la journée sont associées dans l’ordre chronologique aux prises prévues. Par exemple, avec deux prises quotidiennes, la première mesure de la journée complète la première prise et la deuxième mesure complète la seconde. Les mesures supplémentaires restent dans l’historique.

### Avis détaillé

Pendant la période configurée, la grande carte de bienvenue du **Portail** peut indiquer :

- la prochaine prise et son horaire suggéré;
- qu’une prise reste à faire aujourd’hui;
- le nombre de prises complétées et restantes.

L’application n’utilise plus la notion de prise **en retard**. Une mesure faite hors de la plage proposée compte normalement.

L’avis disparaît lorsque toutes les prises prévues sont complétées, lorsque le rappel est désactivé ou lorsque la date se trouve hors de la période choisie.

### Saisie rapide depuis le Portail

Le bouton **Saisir maintenant** ouvre directement l’onglet **Saisie**. La date et l’heure de l’appareil sont proposées et le champ **Systolique** reçoit automatiquement le curseur.

Le bouton **Enregistrer et revenir au Portail** permet d’enregistrer la mesure puis de retourner immédiatement à la page d’accueil.

Ce rappel est seulement un avis visuel dans le Portail. Il ne produit pas de notification poussée sur le téléphone.

### Historique

L’onglet **Historique** permet de choisir une plage de dates, puis de consulter, modifier ou supprimer les mesures du compte connecté.

Chaque fiche affiche :

- l’heure;
- la pression systolique et diastolique;
- le pouls;
- la note facultative.

### Rapport PDF

Dans **Rapport PDF**, inscrivez le **nom complet à imprimer**, puis choisissez la date de début et la date de fin.

Le rapport contient :

- le nom indiqué;
- l’intervalle choisi;
- une ligne pour chaque date de l’intervalle;
- les deux premières mesures de la journée sur la même ligne;
- les mesures supplémentaires sur une ligne marquée **suite**;
- les notes associées;
- la mention **Aucune donnée pour ce jour** lorsqu’aucune mesure n’existe à une date donnée.

### Préparer le courriel

Le bouton **Préparer le courriel** ouvre l’application de messagerie avec un sujet et un texte proposés. Le PDF doit généralement être joint manuellement, car les navigateurs ne permettent pas d’ajouter automatiquement une pièce jointe à un courriel.
""",
    },
    {
        "title": "Personnages JDR",
        "icon": "casino",
        "caption": "Créer une feuille interactive Pathfinder / Ravenloft",
        "keywords": (
            "jdr personnage ravenloft pathfinder feuille force "
            "dextérité constitution intelligence sagesse charisme "
            "classe armure initiative sauvegarde peur horreur folie "
            "compétence attaque points vie"
        ),
        "content": """
### Données privées et plusieurs personnages

Chaque personnage appartient uniquement à l’utilisateur connecté. Il n’est pas partagé avec une famille ou un autre compte pendant la phase 1.

L’utilisateur peut créer plusieurs personnages, passer de l’un à l’autre et supprimer un personnage avec confirmation.

### Identité

L’onglet **Identité** permet de saisir :

- nom du personnage et nom du joueur;
- campagne;
- classe et niveau;
- race, alignement et divinité;
- catégorie de taille;
- âge, genre, taille physique et poids;
- yeux, cheveux et peau;
- points d’expérience.

### Caractéristiques et combat

L’onglet **Combat** contient les six caractéristiques :

- FOR - Force;
- DEX - Dextérité;
- CON - Constitution;
- INT - Intelligence;
- SAG - Sagesse;
- CHA - Charisme.

Le modificateur est calculé automatiquement. Un score temporaire peut être inscrit pour représenter un effet magique, une maladie ou une autre modification temporaire.

La présentation est maintenant plus compacte : les six caractéristiques peuvent tenir sur une seule ligne sur un grand écran. Chaque carte affiche le score, le score temporaire et le modificateur sans occuper inutilement de hauteur. Sur téléphone, les cartes se replacent automatiquement sur deux colonnes, puis une seule lorsque nécessaire.

La phase 1 calcule notamment :

- la classe d’armure totale;
- la classe d’armure de contact;
- la classe d’armure lorsque le personnage est pris au dépourvu;
- l’initiative;
- le **BMO / CMB**;
- le **DMD / CMD**.

### BMO / CMB et DMD / CMD

- **BMO / CMB** : bonus de manœuvre offensive, utilisé pour effectuer une manœuvre de combat;
- **DMD / CMD** : degré de manœuvre défensive, utilisé comme difficulté pour résister à une manœuvre.

**BMO/CMB = BBA + modificateur de Force** — ou Dextérité pour une créature Très petite ou plus petite — **+ modificateur spécial de taille + divers**.

**DMD/CMD = 10 + BBA + modificateur de Force + modificateur de Dextérité + modificateur spécial de taille + bonus de déviation + autres bonus applicables + divers**.

Les bonus d’esquive et les autres bonus applicables doivent être inscrits dans **Divers – DMD/CMD**. Les pénalités négatives inscrites dans **Divers CA** sont appliquées automatiquement au DMD/CMD.

Les champs de **Combat et défenses** sont plus courts et plus denses. Les valeurs numériques, généralement limitées à quelques chiffres, sont regroupées sur davantage de colonnes sur ordinateur et se replacent proprement sur téléphone.

### Règles de calcul intégrées

Un bouton **Règles de calcul**, placé près des boutons d’enregistrement, ouvre une aide détaillée destinée aux joueurs moins familiers avec Pathfinder ou Ravenloft.

La fenêtre regroupe :

- le calcul des modificateurs de caractéristiques;
- la CA totale, la CA de contact et la CA pris au dépourvu;
- l’initiative;
- le BMO/CMB et le DMD/CMD;
- Vigueur, Réflexes, Volonté, Peur, Horreur et Folie;
- les compétences;
- les bonus d’attaque.

Chaque rubrique présente la formule générale et, lorsque des données sont disponibles, un exemple calculé avec les valeurs du personnage actuel.

### Jets de sauvegarde Ravenloft

L’onglet **Sauvegardes** comprend :

- Vigueur;
- Réflexes;
- Volonté;
- Peur;
- Horreur;
- Folie.

Le total combine automatiquement le bonus de base, la caractéristique correspondante, la magie, les modificateurs divers et temporaires. Un champ permet de conserver les modificateurs conditionnels.

### Compétences Pathfinder

La liste de départ utilise maintenant les compétences de Pathfinder 1re édition, notamment Acrobaties, Perception, Discrétion, Linguistique et les différentes Connaissances.

Pour chaque compétence, l’utilisateur peut modifier :

- le nom;
- la caractéristique associée;
- les rangs entiers;
- le modificateur divers;
- le statut de compétence de classe;
- la formation requise;
- l’application de la pénalité d’armure.

Une compétence est considérée comme **possédée** lorsqu’au moins 1 rang y est investi. Une compétence de classe possédée reçoit automatiquement le bonus Pathfinder de **+3**.

### Filtres rapides

Quatre filtres permettent de réduire la longue liste :

- **Mes compétences** : seulement les compétences avec au moins 1 rang;
- **Compétences de classe** : toutes les compétences cochées comme compétences de classe;
- **Sans rang** : les compétences où aucun rang n’est encore investi;
- **Toutes** : l’ensemble de la liste.

Un champ de recherche permet aussi de retrouver rapidement une compétence. La recherche fonctionne autant avec le nom français qu’avec le nom anglais.

### Noms français et anglais

Le nom français et le nom anglais sont affichés sur une seule ligne compacte.

Exemples :

- **Acrobaties — Acrobatics**;
- **Sabotage — Disable Device**;
- **Psychologie — Sense Motive**;
- **Escamotage — Sleight of Hand**;
- **Art de la magie — Spellcraft**.

Le petit bouton de modification permet d’ouvrir une fenêtre pour corriger séparément les deux noms. Lors de l’ajout d’une compétence personnalisée, le nom anglais demeure facultatif.

Des pastilles compactes indiquent **Possédée**, **Classe**, **Formation** et **Armure**.

### Présentation compacte

Les champs **Carac.**, **Rangs** et **Divers**, ainsi que les cases **Classe**, **Formation**, **Armure** et **×2**, sont placés sur une seule ligne lorsque la largeur de l’écran le permet. Sur téléphone, ils se replacent automatiquement sur quelques lignes plus courtes.

### Vérification du calcul

Sous chaque compétence, l’application montre la formule complète utilisée pour calculer le total.

Exemple pour Dressage / Handle Animal :

```text
CHA -2 + rangs +1 + classe +3 + divers +0 = total +2
```

Le bonus de compétence de classe de **+3** est ajouté automatiquement lorsque la compétence possède au moins 1 rang. Il ne faut donc pas inscrire ce bonus une deuxième fois dans **Divers**.

Lorsque l’application détecte une compétence de classe possédée avec **Divers +3**, elle affiche un avertissement et un bouton permettant de remettre rapidement **Divers** à zéro. Aucun changement n’est appliqué automatiquement, car un bonus divers de +3 peut parfois être légitime.

Lors de la migration, les anciennes compétences D&D 3.5 sans données sont remplacées par la liste Pathfinder. Une ancienne compétence contenant déjà des rangs ou des modificateurs est conservée comme compétence personnalisée avec la mention **ancienne 3.5**, afin de ne perdre aucune donnée.

### Attaques

L’utilisateur peut enregistrer autant d’attaques que nécessaire avec :

- nom;
- caractéristique utilisée;
- bonus magique et divers;
- dégâts;
- critique;
- portée;
- type;
- notes;
- munitions actuelles et maximums.

Le bonus total d’attaque combine le bonus de base à l’attaque, le modificateur de caractéristique, la taille, la magie et les modificateurs divers.

### Limites de la phase 1

L’équipement, les dons, les capacités spéciales, les langues, les sorts, l’impression PDF, la progression avancée et les groupes de campagne seront ajoutés dans les phases suivantes.

La feuille est inspirée de la structure fournie, mais l’interface est adaptée aux téléphones et aux ordinateurs plutôt que de reproduire exactement la mise en page du document papier.
""",
    },
    {
        "title": "Familles et partage",
        "icon": "groups",
        "caption": "Espaces de données partagés",
        "keywords": (
            "famille partage membres propriétaire accès changer "
            "famille active"
        ),
        "content": """
### Principe

Chaque famille possède ses propres items, besoins, magasins, catégories, modèles et recettes. Les membres autorisés voient les mêmes données et peuvent collaborer.

### Choisir la famille active

Plusieurs pages affichent un sélecteur **Famille**. Le changement de famille recharge la page avec les données de l'espace choisi.

### Gestion des familles

Dans le Portail, ouvrez **Familles** pour :

- créer une famille;
- choisir la famille active;
- renommer une famille lorsque votre rôle le permet;
- gérer les accès partagés;
- consulter des statistiques;
- supprimer une famille avec confirmation.

La création des comptes et l'attribution des familles sont réservées aux utilisateurs autorisés.
""",
    },
    {
        "title": "Items",
        "icon": "inventory_2",
        "caption": "Créer et gérer le catalogue familial",
        "keywords": (
            "item ajouter modifier supprimer recherche quantité note "
            "magasin catégorie besoin fréquent"
        ),
        "content": """
### Ajouter un item

Dans **Items**, inscrivez le nom, la quantité, le magasin et la catégorie, puis touchez **Ajouter**. Une note facultative peut préciser le format, la marque ou une préférence.

### Rechercher et trier

Le champ **Rechercher un item** filtre instantanément par nom ou catégorie. Le menu de tri permet un classement alphabétique, par ordre d'ajout ou par catégorie.

### Ajouter ou retirer des besoins

Touchez la partie principale d'une ligne pour changer son statut. Le cercle vert indique que l'item est déjà dans les besoins.

### Modifier ou supprimer

- Crayon : modifier le nom, la quantité, le magasin, la catégorie, la note ou le statut;
- Corbeille : placer l'item dans la corbeille.

Les items supprimés peuvent être restaurés depuis **Activité et corbeille** pendant leur période de conservation.

### Items fréquents

Les produits souvent ajoutés peuvent être proposés comme raccourcis. Un toucher les replace dans les besoins sans créer de doublon.


### Tri alphabétique

Le tri **Alphabétique** est insensible aux majuscules et aux accents.

Par exemple, Café, Céréales et Concombre sont classés selon leurs lettres normales, sans repousser les mots accentués à la fin. L’orthographe originale reste affichée.
""",
    },
    {
        "title": "Besoins",
        "icon": "shopping_cart",
        "caption": "Préparer la liste d'achats",
        "keywords": (
            "besoins liste acheter catégories fermer ouvrir crochet "
            "annuler magasin"
        ),
        "content": """
### Consulter les besoins

Les articles sont regroupés selon leur magasin et leur catégorie. Les noms longs passent automatiquement sur plusieurs lignes.

### Ouvrir ou fermer les groupes

Touchez l'en-tête d'un groupe pour le déployer ou le replier. Les boutons avec flèches permettent d'ouvrir ou de fermer tous les groupes.

### Retirer un article

Touchez la ligne ou le crochet vert. L'article est retiré des besoins. Le bouton **Annuler** demeure disponible brièvement pour corriger une erreur.

### Commencer les courses

Le bouton **Commencer les courses** ouvre un écran simplifié conçu pour l'utilisation en magasin.
""",
    },
    {
        "title": "Mode courses",
        "icon": "shopping_cart_checkout",
        "caption": "Cocher les achats en magasin",
        "keywords": (
            "mode courses progression acheté panier synchronisation "
            "actualisation terminer reprendre"
        ),
        "content": """
### Démarrer ou reprendre

Depuis **Besoins**, utilisez **Commencer les courses**. Une session interrompue peut être reprise avec **Reprendre les courses**.

### Pendant les achats

- La progression indique le nombre d'articles achetés et restants.
- Touchez toute une ligne lorsque l'article est placé dans le panier.
- Le dernier article coché peut être restauré avec **Annuler**.
- Un groupe terminé disparaît automatiquement.
- La liste s'actualise régulièrement pour afficher les changements faits par un autre membre.
- Lorsqu’un nouvel item est ajouté aux besoins pendant que vous êtes en **Mode courses**, un avis apparaît avec son nom.
- Le magasin et, lorsque cette fonction est active, la catégorie du nouvel item sont ouverts automatiquement afin qu’il soit facile à repérer.

L’avis est affiché seulement pour un véritable ajout détecté pendant la session. Restaurer vous-même un article avec **Annuler** ne produit pas un faux avis.

Lorsque les catégories sont désactivées pour la famille, le Mode courses regroupe les articles directement par magasin.

### Actualisation automatique

Le Mode courses vérifie périodiquement si de nouveaux items ont été ajoutés. Cette vérification s’arrête automatiquement lorsque l’utilisateur quitte la page, afin d’éviter qu’une tâche liée à une ancienne page continue de fonctionner.

Le bouton **Actualiser** reste disponible en tout temps pour forcer immédiatement une nouvelle vérification.

### Terminer

**Terminer les courses** ferme la session. Les articles non achetés demeurent dans les besoins.
""",
    },
    {
        "title": "Magasins et catégories",
        "icon": "category",
        "caption": "Organiser les produits et le trajet",
        "keywords": (
            "magasin catégorie créer renommer ordre fusion supprimer "
            "trier trajet"
        ),
        "content": """
### Différence

- **Magasin** : lieu où le produit est normalement acheté, par exemple IGA ou Costco;
- **Catégorie** : type ou rayon du produit, par exemple Produits laitiers ou Fruits et légumes.

### Catégories facultatives par famille

Dans **Organisation**, l’interrupteur **Utiliser les catégories** s’applique à toute la famille.

Lorsqu’il est désactivé :

- les champs et filtres de catégorie sont masqués;
- Items, Besoins et Mode courses utilisent seulement les magasins;
- les catégories existantes et leurs associations sont conservées;
- les nouveaux items sont liés à une catégorie technique invisible;
- la fonction peut être réactivée plus tard sans perdre les anciennes données;
- les autres familles peuvent continuer à utiliser les catégories.

### Gestion

Lorsque les catégories sont actives, la page **Organisation** permet de les créer, renommer, réordonner, fusionner ou supprimer. L’onglet des magasins offre des fonctions comparables.

Lorsque les catégories sont désactivées, la page affiche uniquement les magasins et le réglage permettant de les réactiver.

### Ordre personnalisé

Les flèches permettent de placer les magasins et catégories dans l'ordre rencontré pendant les courses. Cet ordre est repris dans **Besoins** et dans le **Mode courses**.

Avant une suppression, les items associés doivent être réattribués ou la fonction de fusion doit être utilisée.
""",
    },
    {
        "title": "Listes modèles",
        "icon": "checklist",
        "caption": "Réutiliser des listes préparées",
        "keywords": (
            "liste modèle créer depuis besoins ajouter item quantité "
            "réordonner déployer"
        ),
        "content": """
### Créer une liste modèle

Deux possibilités :

- **Nouvelle liste modèle** : crée une liste vide;
- **Créer depuis les besoins** : copie tous les besoins actuels.

### Ajouter et organiser les items

Déployez une liste modèle, choisissez un item existant, sa quantité, puis utilisez **Ajouter**. La liste demeure déployée pendant que vous la préparez.

Les flèches modifient l'ordre. Le crayon ajuste la quantité. Le X retire seulement la ligne de la liste modèle; l'item original demeure dans le catalogue familial.

### Utiliser une liste modèle

**Ajouter aux besoins** traite toute la liste en une opération. Les items déjà présents ne sont pas dupliqués. Leur quantité est augmentée seulement lorsque le modèle en demande davantage.

### Publier dans la bibliothèque partagée

Cochez **Publier dans la bibliothèque partagée** pour créer une version publique sécurisée. Utilisez **Mettre à jour la version publiée** après une modification que vous souhaitez rendre visible. Décochez la case pour retirer la publication; les copies déjà créées dans d’autres familles demeurent intactes.
""",
    },
    {
        "title": "Recettes",
        "icon": "restaurant_menu",
        "caption": "Associer les recettes aux items",
        "keywords": (
            "recette ingrédient portions préparation ajouter besoins "
            "quantité précision"
        ),
        "content": """
### Créer une recette

Une recette peut contenir :

- un nom;
- une description;
- un nombre de portions;
- des instructions de préparation.

### Ajouter des ingrédients

Déployez la recette, choisissez un item existant, indiquez une quantité et une précision facultative, puis utilisez **Ajouter**. La recette demeure déployée pendant la saisie.

Les flèches changent l'ordre des ingrédients. Le crayon modifie la quantité ou la précision. Le X retire l'ingrédient de la recette sans supprimer l'item familial.

### Ajouter aux besoins

**Ajouter les ingrédients** transfère tous les ingrédients vers les besoins sans créer de doublons.

### Publier dans la bibliothèque partagée

Cochez **Publier dans la bibliothèque partagée** pour publier une copie sécurisée de la recette. La publication n’inclut pas les magasins, notes privées, prix, besoins ou identifiants internes. Une famille qui copie la recette reçoit une version privée et indépendante.
""",
    },
    {
        "title": "Bibliothèque partagée",
        "icon": "public",
        "caption": "Consulter et copier les publications",
        "keywords": (
            "bibliothèque partagée publique publier recette liste modèle "
            "copier famille aperçu recherche"
        ),
        "content": """
### Consulter la bibliothèque

Ouvrez **Bibliothèque partagée** depuis le Portail, les Listes modèles ou les Recettes. Vous pouvez rechercher un nom, un item, un ingrédient ou une catégorie, puis filtrer les recettes et les listes modèles.

### Copier dans votre famille

Utilisez **Consulter et copier** pour voir le contenu avant de le copier. L’application réutilise les items portant exactement le même nom dans votre famille et crée les items manquants. La copie est privée et indépendante : vous pouvez la modifier sans affecter la publication originale.

### Retrait d’une publication

Lorsqu’un auteur décoche la publication, celle-ci disparaît de la bibliothèque. Les copies déjà importées dans les autres familles ne sont jamais supprimées.
""",
    },
    {
        "title": "Activité et corbeille",
        "icon": "history",
        "caption": "Consulter et restaurer",
        "keywords": (
            "activité historique corbeille restaurer supprimer définitivement "
            "actions utilisateurs"
        ),
        "content": """
### Historique

L'historique indique les actions importantes effectuées dans la famille, par exemple l'ajout d'un besoin, la modification d'un item ou la création d'un magasin.

### Corbeille

Les items, catégories ou magasins supprimés peuvent être conservés temporairement.

Selon le type d'élément, vous pouvez :

- le restaurer;
- examiner les dépendances;
- le supprimer définitivement.

La suppression définitive ne peut normalement pas être annulée.
""",
    },
    {
        "title": "Données, importation et exportation",
        "icon": "settings",
        "caption": "Sauvegarder et transférer les données",
        "keywords": (
            "données sauvegarde exporter json csv importer restauration "
            "version 3 famille"
        ),
        "content": """
### Exporter

La page **Données et sauvegarde** permet de choisir une famille et un format :

- **JSON** : sauvegarde complète restaurable;
- **CSV** : tableau lisible des items.

Les sauvegardes JSON actuelles incluent les magasins, catégories, notes, items, besoins, listes modèles et recettes. L’état de publication dans la bibliothèque n’est pas restauré automatiquement : après une importation, republiez volontairement les contenus désirés.

### Importer

L'importation utilise un fichier JSON. Elle agit sur la famille active et demande une confirmation avant de remplacer ou ajouter des données selon le fonctionnement affiché.

### Bonne pratique

Faites une exportation JSON avant :

- une migration importante;
- une requête SQL manuelle;
- une importation;
- un changement majeur de structure.
""",
    },
    {
        "title": "Compte et sécurité",
        "icon": "account_circle",
        "caption": "Profil, mot de passe et sessions",
        "keywords": (
            "compte nom courriel mot passe sécurité déconnexion profil"
        ),
        "content": """
### Mon compte

La page **Mon compte** permet de modifier :

- le nom affiché;
- l'adresse courriel;
- le mot de passe.

Utilisez un mot de passe unique et difficile à deviner. Déconnectez-vous sur un appareil partagé.

### Accès aux données

L'utilisateur ne voit que les familles auxquelles il a été associé. Les données propres à chaque famille demeurent séparées.
""",
    },
    {
        "title": "Administration des utilisateurs",
        "icon": "manage_accounts",
        "caption": "Fonctions réservées aux administrateurs",
        "keywords": (
            "administrateur utilisateurs créer compte activer désactiver "
            "rôle famille accès"
        ),
        "admin_only": True,
        "content": """
### Utilisateurs

Un administrateur peut notamment :

- créer un compte;
- attribuer ou retirer des accès aux familles;
- choisir les applications visibles et utilisables par chaque utilisateur;
- gérer les rôles autorisés;
- activer ou désactiver un utilisateur;
- consulter les informations nécessaires à l'administration.

### Applications accessibles

Le bouton **Applications** dans la fiche d’un compte permet d’autoriser :

- Liste d’épicerie;
- Journal de pression;
- Finances;
- Personnages JDR.

Une application non autorisée ne paraît pas dans le Portail et ses écrans sont bloqués. Les applications encore en développement peuvent être attribuées à l’avance; elles affichent alors **Bientôt**.

Un administrateur du portail possède automatiquement tous les accès.

Les mots de passe ne doivent jamais être communiqués ou conservés en clair.
""",
    },
    {
        "title": "Centre de maintenance",
        "icon": "health_and_safety",
        "caption": "Diagnostic de la base",
        "keywords": (
            "maintenance diagnostic doublons intégrité inutilisés "
            "taille base administrateur"
        ),
        "admin_only": True,
        "content": """
### Diagnostic

Le Centre de maintenance actuel travaille en lecture seule. Il peut signaler :

- références invalides;
- doublons exacts ou probables;
- catégories et magasins inutilisés;
- noms vides ou mal normalisés;
- éléments expirés dans la corbeille;
- familles sans propriétaire ou membre actif;
- taille approximative de la base et de ses tables.

Aucune correction automatique n'est effectuée dans cette première phase.
""",
    },
    {
        "title": "Dépannage",
        "icon": "support",
        "caption": "Problèmes courants",
        "keywords": (
            "dépannage actualiser cache erreur déploiement connexion "
            "pwa canner"
        ),
        "content": """
### Une modification n'apparaît pas

- Actualisez la page;
- sur ordinateur, utilisez une actualisation complète;
- dans la PWA, fermez puis rouvrez l'application.

### L'application ne répond plus

Vérifiez la connexion Internet. Une page hors connexion peut apparaître lorsque le serveur est inaccessible.

### Une liste partagée semble en retard

Dans le Mode courses, utilisez l'icône d'actualisation. Les autres pages peuvent être rechargées en changeant d'onglet ou en actualisant.

### Après un déploiement

Attendez la fin du déploiement Canner avant de tester. En cas d'échec, consultez les dernières lignes du journal d'exécution.
""",
    },
]


def manual_panel(show_heading=True):
    user = get_current_user()
    is_admin = bool(
        user
        and user.get("is_admin")
    )

    if show_heading:
        with ui.row().classes(
            "w-full items-start justify-between gap-3 flex-wrap"
        ):
            with ui.column().classes("gap-0"):
                ui.label(
                    "Manuel d’utilisation"
                ).classes(
                    "text-2xl font-bold"
                )
                ui.label(
                    "Guide du Portail JF Apps et de toutes les applications."
                ).classes(
                    "text-sm text-gray-500"
                )

            ui.icon(
                "help_center"
            ).classes(
                "text-4xl text-primary"
            )

    with ui.card().classes(
        "w-full p-4 border-l-4 border-primary"
    ):
        ui.label(
            "Ce manuel couvre les fonctions actuellement disponibles."
        ).classes(
            "font-bold"
        )
        ui.label(
            "La liste d’épicerie, le Journal de pression, Finances, "
            "Personnages JDR et les fonctions communes du Portail "
            "sont documentés dans cette page."
        ).classes(
            "text-sm text-gray-600"
        )

    organization_diagram(
        compact=True,
    )

    with ui.row().classes(
        "w-full justify-end"
    ):
        ui.button(
            "Ouvrir le parcours complet",
            icon="rocket_launch",
            on_click=lambda: ui.navigate.to(
                "/?tab=demarrage"
            ),
        ).props(
            "outline color=primary"
        )

    search_state = {
        "value": "",
    }

    search_input = ui.input(
        label="Rechercher dans le manuel",
        placeholder=(
            "Ex. modèles, sauvegarde, courses…"
        ),
    ).props(
        "clearable debounce=150 "
        "autocomplete=off"
    ).classes(
        "w-full"
    )

    with search_input.add_slot(
        "prepend"
    ):
        ui.icon("search")

    @ui.refreshable
    def render_sections():
        query = (
            search_state["value"]
            .strip()
            .casefold()
        )

        available_sections = [
            section
            for section in MANUAL_SECTIONS
            if (
                is_admin
                or not section.get(
                    "admin_only",
                    False,
                )
            )
        ]

        if query:
            visible_sections = [
                section
                for section in available_sections
                if query
                in (
                    section["title"]
                    + " "
                    + section["caption"]
                    + " "
                    + section["keywords"]
                    + " "
                    + section["content"]
                ).casefold()
            ]
        else:
            visible_sections = (
                available_sections
            )

        ui.label(
            (
                f"{len(visible_sections)} rubrique"
                if len(visible_sections) == 1
                else (
                    f"{len(visible_sections)} rubriques"
                )
            )
        ).classes(
            "text-sm text-gray-500"
        )

        if not visible_sections:
            with ui.card().classes(
                "w-full p-6 items-center text-center"
            ):
                ui.icon(
                    "search_off"
                ).classes(
                    "text-4xl text-gray-400"
                )
                ui.label(
                    "Aucune rubrique trouvée"
                ).classes(
                    "text-lg font-bold"
                )
                ui.label(
                    "Essayez un autre mot."
                ).classes(
                    "text-gray-500"
                )
            return

        for index, section in enumerate(
            visible_sections
        ):
            with ui.expansion(
                text=section["title"],
                caption=section["caption"],
                icon=section["icon"],
                value=(
                    not query
                    and index == 0
                ),
            ).props(
                "expand-separator"
            ).classes(
                "w-full bg-white rounded-xl "
                "shadow-sm border border-gray-200 "
                "overflow-hidden mt-2"
            ):
                ui.markdown(
                    section["content"]
                ).classes(
                    "w-full px-3 pb-3"
                )

    def search_changed(event):
        search_state["value"] = (
            event.value or ""
        )
        render_sections.refresh()

    search_input.on_value_change(
        search_changed
    )

    render_sections()
