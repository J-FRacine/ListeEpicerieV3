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

### Dépannage — page 404 après un déploiement

Le Portail doit répondre à l’adresse principale `/` ainsi qu’aux adresses contenant un onglet, par exemple `/?tab=items`.

La correction Portail V1.2.1 restaure explicitement cette route principale. Une page 404 immédiatement après le déploiement indique généralement que cette route n’a pas été chargée ou que le déploiement n’est pas encore terminé.

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

### Statistiques techniques Canner

JF Apps charge le script officiel **Canner Web Vitals** dans l’en-tête commun afin de permettre à l’hébergeur d’afficher ses statistiques techniques et de performance. Le script est chargé de façon asynchrone sur toutes les pages et ne modifie pas les données des applications ni les données PostgreSQL.

Sur téléphone, l’en-tête est volontairement réduit à :

- le logo;
- le nom de l’application;
- sa version;
- le bouton **Portail**;
- un menu **Plus**.

Le menu Plus contient Commentaires, Aide, Mon compte, Nouveautés, Installer JF Apps et Déconnexion. Un indicateur peut signaler les commentaires non lus.

### Centre de maintenance et sauvegarde globale

L’action **Sauvegarder toutes mes données** se trouve maintenant dans le **Centre de maintenance**. Depuis l’accueil du Portail, ouvrez **Centre de maintenance**, puis utilisez **Créer la sauvegarde**. Une seule archive ZIP privée est créée avec les données des applications auxquelles le compte a accès. Les fichiers sont séparés par application et un `manifest.json` conserve la date de sauvegarde et les versions.

Le Centre de maintenance est accessible à tous les utilisateurs pour cette sauvegarde privée. Les diagnostics de la base de données restent réservés aux administrateurs. Pour la Liste d’épicerie, seules les familles accessibles au compte sont incluses. Aucune donnée d’une famille ou d’un utilisateur non autorisé n’est exportée. La restauration globale contrôlée reste une évolution future.

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
        "title": "Finances — V1.12.0",
        "icon": "account_balance_wallet",
        "caption": "Prévisions, Budget, financements et prêts partagés",
        "keywords": (
            "finances budget prévisions pourcentage kpi financement intérêts "
            "archives à venir paies prêts partagés catégorie étiquette saisie rapide"
        ),
        "content": """
### KPI du Tableau

Les KPI de dépenses affichent maintenant la part en **% du total prévu** de chaque catégorie. La ligne **Total des KPI affichés** vaut 100 %. Pour les étiquettes, le pourcentage reste indicatif puisque plusieurs étiquettes peuvent s’appliquer à une même transaction.

Le nom d’une catégorie ou d’une étiquette est cliquable : il ouvre la liste des transactions correspondantes pour le mois affiché, séparées entre réalisé et à venir, avec accès à la modification des transactions réelles.

### Saisie rapide

Dans la liste des catégories et des étiquettes, choisissez **+ Ajouter une catégorie…** ou **+ Ajouter une étiquette…** pour créer l’élément directement depuis la Saisie rapide. Après création, il est automatiquement sélectionné pour la transaction en cours.

### Budget

La navigation affiche maintenant le **mois réellement consulté** entre les flèches. Pour un revenu lié à une récurrence aux deux semaines, le nombre de paies est calculé avec les occurrences réelles : un mois peut donc contenir 2 ou 3 paies.

Les dépenses fixes sont séparées en :

- **Dépenses fixes actives** : postes applicables au mois affiché;
- **À venir** : postes dont la période n’a pas encore commencé;
- **Archives** : postes dont la date de fin est antérieure au mois affiché.

Chaque section affiche son propre **total / mois** et **total / paie**. Les totaux À venir et Archives sont informatifs et ne sont pas réintégrés au disponible courant.

La section **Prévisions** projette jusqu’à six mois avec le disponible de base, le report du mois précédent, les dépenses variables prévues/réalisées et le solde estimé de fin de mois. Les dépenses fixes ne sont pas recomptées puisqu’elles sont déjà absorbées dans le Reste par paie.

### Financements

L’onglet **Financements** affiche en haut **Paiements du mois** et **Soldes restants**.

Dans Budget, un poste spécial de type **Financements** peut regrouper plusieurs plans existants. Le montant du groupe est recalculé selon les versements applicables au mois affiché. Un financement ne peut normalement appartenir qu’à un seul groupe, ce qui évite le double comptage. Les transactions restent visibles dans l’Historique, les comptes/cartes et la conciliation, mais elles ne sont plus recomptées comme dépenses variables lorsqu’elles sont déjà absorbées par un groupe Budget.

Lorsqu’un taux d’intérêt est supérieur à 0 %, le formulaire demande si le versement saisi **inclut déjà les intérêts**. Si la réponse est Non, Finances calcule un versement total estimé à partir du solde, du taux annuel, de la fréquence et du nombre de versements restants. Les produits à taux variable, intérêts différés, frais particuliers ou promotions non standards peuvent nécessiter un ajustement manuel.

### Prêts partagés

L’onglet **Prêts partagés** crée un prêt indépendant des autres données Finances. Seuls le propriétaire et les utilisateurs explicitement associés au prêt peuvent le consulter. Chaque participant peut avoir un rôle et une permission propres au prêt. Le module conserve le solde, les mouvements et une projection d’amortissement sans donner accès aux comptes, cartes, Budget, transactions ou autres prêts.
""",
    },
    {
        "title": "Finances — V1.11.0",
        "icon": "account_balance_wallet",
        "caption": "Budget, trésorerie, dépenses, prévisions et conciliation",
        "keywords": (
            "finances dépenses revenus récurrences catégories "
            "sous-catégories étiquettes objectifs report csv json "
            "paiement conciliation carte crédit KPI relevé "
            "solde prévu cumulatif séance historique ajustement "
            "postdaté à venir total prévu projection "
            "cliquable détail transaction ajouter catégorie étiquette saisie rapide "
            "compte bancaire trésorerie budget mensuel aux deux semaines paie "
            "solde minimum hors budget transfert paiement carte "
            "récurrence liée budget synchronisé programmée banque rappel notification push "
            "kpi configurable tableau catégorie étiquette marge crédit limite disponible "
            "supprimer récurrence recalcul projection historique confirmé "
            "paiement carte lié compte départ carte destinataire crédit conciliation "
            "programmé tableau compact transactions à venir repliable "
            "conciliation compte bancaire vu case cocher confirmer concilier "
            "sélection persistante ajout modification tri date ascendante descendante "
            "écart justifié différence relevé référence reporter écart "
            "brouillon conciliation reprendre enregistrer travail paiement programmer arrondir "
            "financement estimation versements fin prévue modalité montant recherche doublons non conciliées mois"
        ),
        "content": """
### Objectif de Finances

**Finances V1.11.0** conserve et complète le principe directeur : **Budget = dépenses fixes et capacité disponible**; **Tableau = suivi des dépenses variables du mois**. La conciliation améliorée de V1.9 reste entièrement conservée.

Le Tableau affiche maintenant le **Reste par paie**, le **Disponible ce mois** selon le nombre de paies détectées, les dépenses variables réalisées et à venir, leur total prévu et le **Reste disponible ce mois**. Le bloc KPI revenus est retiré du Tableau seulement; les revenus restent présents dans l’Historique, les récurrences et les calculs du Budget.

Le correctif de démarrage introduit en V1.6.2 est conservé : une erreur propre à la mise à niveau Finances ou aux rappels Web Push ne doit pas empêcher le Portail JF Apps complet de démarrer.

**Finances** sert au suivi personnel des dépenses, des revenus, des prévisions, du budget global et de la trésorerie. La V1.6 a ajouté la vue de compte bancaire et le budget global; la V1.6.1 a ajouté le lien Budget–Récurrence, les transactions programmées à la banque et les rappels Web Push.

L’application demeure volontairement plus simple qu’une comptabilité complète : elle ne demande pas d’écritures comptables en partie double et ne transforme pas les mouvements personnels en système comptable professionnel.

### Budget fixe et capacité disponible

L’onglet **Budget** sert principalement aux revenus récurrents et aux dépenses fixes. Chaque poste peut avoir une **date de début** et une **date de fin** facultatives. Cela permet, par exemple, de conserver un loyer valide jusqu’au 30 juin et un nouveau montant à partir du 1er juillet sans réécrire les mois passés.

Le Budget calcule le reste mensuel et le **Reste par paie**. Lorsqu’un revenu aux deux semaines est lié à une récurrence, JF Apps utilise les dates réelles/projetées pour déterminer si le mois affiché contient **2 ou 3 paies**. Le Tableau reçoit alors le **Disponible ce mois** correspondant.

Lors de l’ajout ou de la modification d’un poste Budget, **Récurrence associée** permet maintenant de choisir **+ Créer une nouvelle récurrence**. La fréquence, les dates, le mode de paiement, la catégorie, les étiquettes, le mode de confirmation, l’indicateur Programmé et le rappel peuvent être définis dans la même fenêtre. Le poste et sa récurrence sont enregistrés dans une seule transaction afin de ne pas laisser de récurrence orpheline en cas d’erreur.

Lorsque **Synchroniser le montant et la date de fin avec la récurrence** est actif, le montant du poste suit la règle de récurrence et la date de fin du poste Budget est aussi appliquée à la récurrence. Si cette date est raccourcie, seules les occurrences **Prévues** situées après la nouvelle fin sont retirées; les transactions confirmées et l’historique ne sont jamais supprimés automatiquement.

### Tableau — dépenses variables

Le **Tableau** est le poste de pilotage des dépenses variables. Les dépenses fixes déjà représentées par un poste Budget lié à une récurrence ne sont pas comptées une deuxième fois dans ces KPI variables.

Les KPI de dépenses utilisent **Réalisé / À venir / Total prévu** et affichent au bas des catégories une ligne **Total des KPI affichés**. Les étiquettes peuvent compter une même transaction plusieurs fois lorsqu’elle possède plusieurs étiquettes; leur total doit donc être interprété comme un total d’affichage.

L’option **Reporter le solde positif ou négatif au mois suivant** permet de conserver le résultat variable d’un mois. Lorsqu’elle est activée, le mois affiché devient le premier mois du cycle : il n’a pas de report entrant, mais son **Reste disponible ce mois** devient le report du mois suivant. Le Tableau montre alors séparément **Disponible de base**, **Report du mois précédent** et **Disponible ajusté ce mois**. Un report positif augmente la capacité du mois suivant; un report négatif la réduit.

Les valeurs négatives des KPI affichent toujours explicitement le signe **-** en plus de leur couleur.

### Financements et achats en versements

L’onglet **Financements** permet de documenter un financement de magasin ou un plan de versements offert par une carte de crédit, avec ou sans intérêts/frais. Il est possible de saisir un plan neuf ou déjà en cours : montant initial, nombre total de versements, solde restant, prochaine échéance, fréquence, montant du versement, taux/frais, mode de paiement, catégorie et étiquettes.

Le champ **Versements déjà effectués** est facultatif. Si vous connaissez cette valeur, vous pouvez la saisir. Si vous la laissez vide, Finances estime la progression à partir du montant initial, du solde restant actuel et du montant du versement. La fiche indique alors que le nombre de versements est une **estimation**. Lorsqu’un nombre saisi manuellement ne concorde pas avec les montants, un avertissement présente le nombre estimé, le solde théorique et l’écart; vous pouvez toutefois conserver la valeur saisie, notamment pour les plans comportant intérêts, frais ou versements variables.

Chaque carte de financement affiche aussi la **modalité de paiement** (fréquence, montant du versement et compte/carte utilisé), la **prochaine échéance** et une **date de fin prévue** calculée à partir des versements restants.

Par défaut, chaque versement futur est une **vraie dépense prévue** : il apparaît dans les KPI du mois selon sa catégorie et réduit le montant disponible. Le montant initial complet n’est pas ajouté en plus des versements, ce qui évite le double comptage. Un financement peut exceptionnellement être marqué **Hors budget**. Les anciennes mensualités d’un plan déjà commencé ne sont pas recréées automatiquement.

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
- un statut de conciliation;
- l’option **Hors budget**;
- l’indicateur **Programmée dans le compte bancaire** pour une transaction prévue;
- un rappel facultatif le jour prévu, avec heure configurable.

Les champs principaux sont compacts pour faciliter l’utilisation sur téléphone.

L’option **Hors budget** sert surtout aux transferts entre comptes, aux paiements de cartes de crédit et aux déplacements d’épargne. Le mouvement peut continuer à modifier le solde du compte bancaire associé, mais il est exclu des dépenses, revenus, KPI et objectifs afin d’éviter de compter deux fois la même dépense.

La **Saisie rapide** permet aussi de créer une catégorie ou une étiquette sans quitter la transaction en cours.

Dans la liste de catégories, choisissez **+ Ajouter une catégorie…**. Une fenêtre permet d’inscrire le nouveau nom et, au besoin, de le rattacher à une catégorie principale pour en faire une sous-catégorie. La catégorie créée est immédiatement sélectionnée.

Dans la liste d’étiquettes, choisissez **+ Ajouter une étiquette…**. Les étiquettes déjà sélectionnées sont conservées et la nouvelle étiquette est ajoutée à la transaction en cours.

Avant de créer un nouvel élément, JF Apps compare les noms en ignorant les différences évidentes de majuscules, d’accents et d’espaces. Lorsqu’un élément correspondant existe déjà, il est simplement réactivé au besoin et sélectionné.

### Catégories, sous-catégories et étiquettes

Une transaction peut avoir une catégorie ou une sous-catégorie, ainsi que plusieurs étiquettes.

Une même dépense peut compter dans plusieurs objectifs par étiquette. Les objectifs par étiquette ne doivent donc pas être additionnés pour calculer le total général.

### Modes de paiement et comptes bancaires

L’onglet **Organisation** contient une section **Modes de paiement**.

Les valeurs initiales sont :

- **MC Canadian Tire**;
- **MC PC**;
- **Visa Desjardins**;
- **Direct**.

L’utilisateur peut ajouter, renommer, désactiver et réordonner ses propres modes de paiement.

Pour chaque mode, il peut aussi préciser :

- le type : carte de crédit, compte bancaire, **marge de crédit**, argent comptant ou autre;
- le jour habituel de fermeture du relevé;
- le jour habituel de paiement;
- un solde initial ou de référence;
- la date de référence de ce solde;
- une **limite de crédit facultative** lorsqu’il s’agit d’une marge;
- une note.

Pour une **carte de crédit**, le solde initial demeure disponible pour la conciliation. Pour un **compte bancaire**, le solde et sa date de référence servent de point de départ à l’onglet **Compte** et au résumé de trésorerie du Tableau.

Pour une **marge de crédit**, le solde de référence représente la dette déjà utilisée à cette date. Une dépense affectée à la marge **augmente la dette**; un revenu ou remboursement affecté à la marge **réduit la dette**. Si une limite est indiquée, l’application calcule aussi le crédit disponible.

Une transaction utilise un seul mode de paiement. Une transaction récurrente peut mémoriser son mode de paiement par défaut.

### Paiement de carte lié

Utilisez le bouton **Paiement de carte** lorsque vous payez une carte de crédit à partir d’un compte bancaire. Cette saisie est différente d’une dépense ordinaire : elle représente un **transfert lié entre deux comptes**.

Le formulaire demande :

- le **Compte bancaire de départ**;
- la **Carte de crédit à payer**;
- le montant;
- la date du débit bancaire;
- la date de réception sur la carte, qui peut être différente;
- le statut Prévu ou Confirmé;
- l’indicateur **Déjà programmé auprès de la banque**;
- un rappel facultatif le jour du débit;
- une note.

Un seul paiement logique produit deux effets liés :

- une sortie sur le compte bancaire;
- un crédit sur la carte de crédit qui réduit le solde dû.

Le paiement est automatiquement **Hors budget**. Les achats effectués avec la carte ont déjà été comptés comme dépenses; le paiement de la carte ne doit donc pas créer une deuxième dépense budgétaire.

Lorsque le paiement est **Confirmé**, son côté carte apparaît dans **Conciliation** comme un paiement reçu/crédit appliqué. Le montant est soustrait du solde dû de la carte.

Modifier, confirmer ou supprimer le paiement agit sur les deux côtés ensemble. Si l’un des côtés a déjà été concilié, retirez d’abord cette conciliation avant de modifier ou supprimer le paiement lié.

Dans l’Historique, le mouvement est présenté une seule fois, du côté du compte bancaire, avec la relation **Compte → Carte**. Le côté carte technique reste disponible dans Conciliation sans créer une deuxième ligne dans l’Historique général.

### Compte bancaire, marge de crédit et trésorerie

L’onglet **Compte** reproduit la logique d’un suivi mensuel. Pour un compte bancaire, un solde de départ est repris, les entrées et sorties sont placées dans l’ordre chronologique, puis le solde est recalculé après chaque mouvement.

La même vue peut maintenant suivre une **Marge de crédit**. Dans ce cas, le montant affiché est la dette utilisée : une utilisation de la marge augmente ce montant et un remboursement le réduit.

Pour utiliser cette vue, créez ou modifiez un mode de paiement de type **Compte bancaire** ou **Marge de crédit**, puis indiquez son **solde de référence** et la **date de référence** correspondante. Pour une marge, vous pouvez aussi inscrire sa limite.

Pour le mois choisi, l’écran présente :

- le **Solde de départ**;
- le **Solde actuel**;
- le **Plus bas prévu**;
- le **Solde fin de mois**;
- la liste chronologique des entrées et sorties;
- le solde obtenu après chaque mouvement.

Le **Plus bas prévu** est particulièrement utile pour un compte bancaire : un mois peut terminer avec un bon solde tout en passant temporairement très près de zéro avant une paie ou un dépôt.

Pour une **marge de crédit**, l’écran remplace cette logique par **Plus haut prévu**, c’est-à-dire le niveau maximal de dette prévu pendant le mois. Il affiche aussi la dette de fin de mois et, lorsqu’une limite est configurée, le **crédit disponible**.

Les transactions confirmées déjà survenues alimentent le solde actuel. Les transactions prévues, postdatées et les récurrences futures alimentent la projection jusqu’à la fin du mois. Une transaction prévue dont la date est déjà passée reste maintenant visible comme mouvement attendu jusqu’à ce qu’elle soit confirmée, modifiée ou supprimée.

Une transaction marquée **Hors budget** reste visible dans le Compte et modifie son solde si elle utilise ce compte bancaire. Elle n’est toutefois pas comptée comme nouvelle dépense ou nouveau revenu dans le budget et les KPI.

Une transaction prévue peut aussi être marquée **Programmée à la banque**. Cet indicateur signifie que le paiement ou le mouvement a déjà été planifié auprès de l’institution bancaire, mais la transaction reste **Prévue** dans JF Apps jusqu’à ce qu’elle soit confirmée. Dans les listes compactes, notamment l’Historique, le libellé court **Programmé** apparaît directement sur la ligne afin de repérer immédiatement les mouvements déjà planifiés.

#### Conciliation rapide du compte bancaire

Pour un mode de paiement de type **Compte bancaire**, chaque mouvement de l’onglet **Compte** possède maintenant une case **Vu**.

- cochez **Vu** lorsque vous avez réellement constaté le mouvement dans votre compte bancaire;
- une transaction déjà confirmée est simplement marquée **Conciliée**;
- une transaction encore **Prévue** est confirmée et conciliée en une seule opération;
- décocher **Vu** retire la conciliation si vous vous êtes trompé, sans supprimer la transaction;
- une **Récurrence projetée** qui n’existe pas encore comme transaction réelle ne peut pas être cochée.

Cette méthode simplifiée s’applique uniquement aux **comptes bancaires**. Les cartes de crédit continuent d’utiliser l’écran **Conciliation** par relevé.

Chaque transaction réelle du Compte possède aussi une action **Modifier**. Une transaction confirmée non conciliée peut être ouverte directement. Si elle est déjà cochée **Vu**, Finances demande d’abord **Retirer la conciliation et modifier**; la transaction n’est pas supprimée et peut être conciliée de nouveau après la correction. Une ligne qui est encore une **Récurrence projetée** ouvre plutôt la récurrence d’origine, puisqu’elle n’est pas encore une vraie transaction. Un paiement de carte lié ouvre sa fiche de paiement liée; si son côté carte est déjà concilié, cette conciliation doit d’abord être retirée dans l’écran Conciliation.

### Rappels de transactions

Pour une transaction **Prévue**, activez **Me rappeler cette transaction le jour prévu** et choisissez une heure. L’heure proposée par défaut est **09:00**. Si la transaction a déjà été confirmée avant cette heure, aucun rappel n’est envoyé.

Les récurrences peuvent utiliser la même option. Leur rappel est vérifié directement à partir de leur calendrier, même lorsque l’occurrence du jour n’a pas encore été créée dans l’Historique.

Dans l’onglet **Compte**, la carte **Notifications de transactions** permet d’activer ou de désactiver les notifications sur l’appareil courant. Le même abonnement Web Push que Journal de pression est réutilisé lorsqu’il existe déjà, mais les canaux restent indépendants : désactiver les rappels Finances ne désactive pas les rappels du Journal de pression, et inversement. La notification demeure volontairement discrète : **« Finances — Une transaction prévue nécessite votre attention. »**

Sur iPhone/iPad, les notifications Web Push nécessitent que JF Apps soit ajoutée à l’écran d’accueil et que l’autorisation de notification ait été accordée.

La partie annuelle présente les **12 mois** avec le solde de fin et le minimum prévu de chacun. Un mois peut être ouvert directement pour consulter son détail. Les mois antérieurs à la date de référence du compte ne sont pas inventés et restent indisponibles.

### Budget mensuel global

L’onglet **Budget** sert à planifier le budget habituel indépendamment des transactions d’un mois précis.

Chaque ligne est un **revenu** ou une **dépense** et peut être saisie :

- en montant **mensuel**;
- ou en montant **aux deux semaines**.

L’application convertit automatiquement les deux vues sur une base de **26 paies par année** :

- montant aux deux semaines × 26 ÷ 12 = montant mensuel;
- montant mensuel × 12 ÷ 26 = montant aux deux semaines.

Pour une dépense saisie mensuellement, un **montant par paie personnalisé** peut remplacer le calcul automatique. Cela permet par exemple de mettre volontairement un peu plus d’argent de côté à chaque paie pour conserver un coussin de sécurité.

Le résumé affiche :

- les revenus mensuels;
- les dépenses mensuelles;
- le reste disponible mensuel;
- le reste disponible par paie.

Les lignes peuvent être activées, désactivées, réordonnées et modifiées. Pour les **Dépenses fixes**, le menu **Trier par** permet d’afficher les postes selon l’**ordre personnalisé**, l’ordre **alphabétique**, le **montant par mois**, le **montant par paie** ou la **date de début**, en sens croissant ou décroissant. Le tri est uniquement visuel : il ne change pas les données, les récurrences ni les calculs. Les flèches de réorganisation restent disponibles lorsque l’ordre personnalisé est choisi.

Un poste du Budget peut maintenant être associé à une **récurrence existante**. Lorsque **Synchroniser le montant et la date de fin avec la récurrence** est activé, une modification du montant ou de la fréquence de cette récurrence met à jour le poste budgétaire lié et la date de fin du poste est aussi appliquée à la récurrence. Une récurrence mensuelle est reprise comme montant mensuel; une récurrence toutes les deux semaines est reprise comme montant aux deux semaines. Les autres fréquences sont converties en moyenne mensuelle.

Le montant par paie personnalisé demeure disponible pour un poste mensuel synchronisé. La liaison est facultative : les postes comme « Épicerie 600 $/mois » peuvent rester **Budget seulement** sans créer ni nécessiter une transaction. Une même récurrence ne peut être liée qu’à un seul poste budgétaire afin d’éviter les doublons.

Le **Budget** représente la planification globale habituelle; les **Objectifs** demeurent disponibles séparément pour suivre des limites par catégorie ou par étiquette au fil des mois.

### Navigation dans Finances sur téléphone

Le sous-menu de Finances contient plusieurs sections. Sur téléphone, il se présente comme une barre horizontale déroulante.

Les onglets ne sont pas réduits les uns sur les autres. Il est possible de glisser la barre vers la gauche ou la droite pour atteindre :

- Tableau;
- Compte;
- Budget;
- Saisie;
- Historique;
- Récurrences;
- Objectifs;
- Conciliation;
- Organisation;
- Exporter.

Des flèches peuvent aussi apparaître lorsque tous les onglets ne tiennent pas à l’écran.

### Tableau mensuel : réalisé et à venir

Le Tableau distingue trois niveaux pour le mois affiché :

- **Réalisé** : transactions confirmées dont la date est atteinte;
- **À venir** : transactions prévues, postdatées ou issues d’une récurrence future;
- **Total prévu** : Réalisé + À venir.

Lorsque l’utilisateur possède un compte bancaire avec un solde de référence, une bande de trésorerie affiche aussi **Solde de départ**, **Solde actuel**, **Plus bas prévu** et **Fin de mois prévue**, avec accès direct à l’onglet Compte.

Les récurrences actives sont projetées jusqu’à la fin du mois affiché sans créer immédiatement de transactions confirmées. Un revenu récurrent futur apparaît donc dans les prévisions dès qu’il appartient au mois consulté.

La section **Transactions à venir** conserve toujours visibles les trois montants essentiels :

- **Dépenses à venir**;
- **Revenus à venir**;
- **Effet net prévu**.

Les longues listes **Dépenses prévues** et **Revenus prévus** sont maintenant **repliées par défaut** afin de réduire fortement la hauteur du Tableau, surtout sur téléphone. Utilisez **Voir les transactions à venir** pour ouvrir le détail au besoin. Le contrôle indique aussi le nombre de dépenses et de revenus prévus.

Une fois ouvert, le détail montre la date, la description, le mode de paiement, les mentions **Récurrence projetée**, **À confirmer**, **Hors budget** et **Programmé** lorsque pertinentes.

Les KPI par catégorie et par étiquette utilisent les colonnes :

- Réalisé;
- À venir;
- Total prévu.

Dans **Organisation > Catégories** et **Organisation > Étiquettes**, la case **Tableau** permet de choisir individuellement les éléments qui apparaissent dans ces KPI. Décochez une catégorie ou une étiquette pour alléger le Tableau : elle reste entièrement disponible dans les transactions, les filtres, l’historique et les objectifs. Après la mise à jour vers V1.7.0, les éléments existants restent cochés par défaut afin de ne rien masquer automatiquement.

Les transactions **Hors budget** sont exclues de ces montants.

Les dépenses et les revenus sont présentés dans des blocs distincts. Les noms trop longs sont tronqués, mais le nom complet demeure disponible au survol.

Le nom d’une **catégorie** ou d’une **étiquette** est cliquable. La fenêtre de détail affiche les transactions du mois correspondant à cette ligne, séparées en **Réalisé** et **À venir**, avec les trois totaux.

Une transaction réelle peut être ouverte depuis cette fenêtre pour consulter ou modifier sa fiche. Une récurrence future qui n’a pas encore créé de transaction demeure consultative et porte l’indication **Récurrence projetée**.

Une transaction portant plusieurs étiquettes peut apparaître dans plusieurs lignes. Les montants par étiquette ne doivent pas être additionnés pour obtenir le total général.

### Solde prévu cumulatif des modes de paiement

Le **Tableau** conserve le solde prévu pour chaque mode de paiement utilisé pour la conciliation.

Ce calcul ne recommence jamais à zéro au début d’un mois. Il traverse les mois jusqu’à ce que les transactions soient conciliées.

Le solde confirmé non concilié est calculé ainsi :

- dépenses confirmées non conciliées;
- moins les revenus, remboursements et crédits confirmés non conciliés;
- plus l’ajustement initial non concilié.

Les transactions prévues sont présentées séparément et ajoutées au **solde prévu**.

Cette vue de conciliation est distincte du **solde bancaire courant** présenté dans l’onglet Compte.

### Conciliation par relevé

L’onglet **Conciliation** est maintenant destiné principalement aux **cartes de crédit**. Il permet de choisir une carte et d’afficher ses transactions confirmées non conciliées, même lorsqu’elles proviennent de mois différents.

Pendant une séance, l’utilisateur peut :

- cocher une ou plusieurs transactions;
- tout sélectionner ou tout désélectionner;
- trier l’affichage par **Date ascendante** ou **Date descendante**;
- filtrer ou rechercher sans perdre les transactions déjà cochées;
- **ajouter une transaction** directement depuis la conciliation;
- **modifier une transaction** avec le bouton crayon;
- inscrire la date et le solde réel du relevé;
- inscrire la date de paiement et la date réelle de conciliation;
- inclure le solde initial lors de la première séance, au besoin;
- finaliser la sélection en une seule opération.

Une transaction sélectionnée reste cochée après un ajout, une modification, un tri ou un rafraîchissement tant qu’elle demeure **confirmée, non conciliée et affectée à la même carte**. Si une modification la rend inadmissible — par exemple en changeant sa carte — elle est retirée de la sélection avec un avis. Changer volontairement de carte dans le sélecteur démarre une nouvelle sélection.

Une conciliation peut maintenant être **enregistrée en cours**. Le brouillon conserve la carte, les transactions cochées, les dates et le solde du relevé, la date de paiement, la note, l’explication d’écart, les filtres et le tri. Vous pouvez ensuite quitter l’onglet et revenir plus tard avec **Reprendre**. La sauvegarde intermédiaire ne concilie aucune transaction et ne change jamais la référence du relevé. Si une transaction sauvegardée n’est plus admissible au retour, elle est retirée de la sélection avec un avis. Un brouillon peut aussi être **Abandonné**.

#### Solde de référence et différence

À partir de V1.9, la conciliation présente explicitement la formule :

**Solde précédent + mouvements sélectionnés = solde attendu**

Le **solde du relevé** est ensuite comparé au solde attendu. Après la première séance, le dernier relevé finalisé sert normalement de point de départ au relevé suivant.

Si une différence existe, deux choix sont proposés :

- **Clore comme écart justifié** : une explication est obligatoire. Le solde réel du relevé devient la nouvelle référence; l’écart ne se reporte donc pas au mois ou au relevé suivant. L’explication reste uniquement dans l’historique de la séance et ne crée aucune transaction dans l’Historique ordinaire, le Budget, les KPI ou les Objectifs. Cette option convient par exemple à un achat fait pour quelqu’un d’autre que vous ne souhaitez pas suivre dans vos finances personnelles;
- **Reporter l’écart** : le solde attendu demeure la référence. La différence reste donc à résoudre lors d’une prochaine conciliation.

Lorsque la différence est nulle, la séance est simplement enregistrée comme **équilibrée**.

Pour une carte de crédit, **Clore et programmer le paiement** finalise d’abord la conciliation puis ouvre la fiche existante **Paiement de carte**. La carte, le montant du relevé et la date de paiement sont proposés automatiquement, mais rien n’est enregistré sans validation explicite. Le compte bancaire source, le montant, les dates et le statut restent modifiables. Le bouton **Arrondir au dollar supérieur** permet, par exemple, de transformer 417,32 $ en 418,00 $ avant l’enregistrement. Si la conciliation contient un écart, l’action de clôture et paiement utilise la logique d’**écart justifié** et exige donc une explication.

### Historique des conciliations

Chaque séance conserve :

- le mode de paiement;
- la date et le solde du relevé;
- la date de paiement;
- la date de conciliation;
- les transactions sélectionnées;
- le solde de référence précédent;
- le total net des mouvements conciliés;
- le solde attendu;
- le solde réel du relevé;
- la différence;
- le traitement de la différence : équilibrée, écart justifié ou écart reporté;
- l’explication de l’écart justifié, lorsqu’il y en a une;
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

La récurrence peut aussi mémoriser une catégorie, des étiquettes, un mode de paiement par défaut, l’option **Hors budget**, l’indicateur **Programmée à la banque** et un rappel. Lorsqu’une occurrence est créée, elle conserve ces choix.

#### Modifier une récurrence

En V1.7.0, modifier la **date de début**, le **montant**, la **fréquence** ou les autres paramètres d’une récurrence recalcule automatiquement ses occurrences **prévues et non confirmées**. Les anciennes occurrences prévues sont retirées puis reconstruites à partir de la nouvelle règle.

Si cette correction fait apparaître une occurrence à une date déjà passée — par exemple déplacer le début du 20 août au 6 août — l’occurrence rétroactive est créée **À confirmer**, même pour une récurrence normalement automatique. Elle ne devient donc pas silencieusement une transaction déjà réalisée.

Les transactions déjà **confirmées** ne sont jamais réécrites automatiquement : elles représentent l’historique réel. Ainsi, corriger une récurrence du 20 au 6 du mois fait apparaître l’occurrence prévue du 6, mais une transaction déjà confirmée le 20 reste dans l’historique jusqu’à ce que l’utilisateur décide lui-même de la corriger.

#### Supprimer une récurrence

Le bouton **Supprimer** offre deux choix :

- supprimer la récurrence **et ses transactions prévues non confirmées**;
- supprimer seulement la règle et **conserver les transactions prévues comme transactions indépendantes**.

Dans les deux cas, les transactions confirmées sont conservées. Si un poste du Budget était lié à la récurrence supprimée, il devient un poste Budget indépendant au lieu d’être supprimé.

### Objectifs mensuels

Un objectif peut viser une catégorie, une sous-catégorie ou une étiquette.

Chaque objectif possède une politique de report :

- aucun report;
- report du montant inutilisé;
- report du dépassement;
- report des deux.

Un plafond de report facultatif peut être défini. Les mois déjà créés conservent leur montant de base et leur politique même si l’objectif est modifié plus tard.

Les transactions **Hors budget** sont exclues de la progression des objectifs.

### Tableau de bord

Le tableau de bord affiche :

- les dépenses;
- les revenus;
- la différence;
- les transactions prévues;
- le résumé du compte bancaire principal lorsqu’il est configuré;
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

Tous les montants sont alignés à droite. Les descriptions, catégories, étiquettes et modes de paiement restent alignés à gauche. La mention **Hors budget** apparaît lorsque l’option est activée et la mention **Programmé** apparaît lorsqu’une transaction prévue est déjà programmée auprès de la banque. Un paiement de carte lié affiche aussi clairement la relation **Compte → Carte**.

Les filtres permettent de chercher par :

- dates;
- type;
- statut de transaction;
- catégorie;
- étiquette;
- mode de paiement;
- statut de conciliation;
- texte;
- **montant exact**;
- **montant minimum / maximum**.

Les montants peuvent être saisis avec un point ou une virgule décimale. Le signe n’est pas nécessaire : une recherche sur 42,50 compare le montant enregistré des dépenses comme des revenus.

Le bouton **Rechercher les doublons** repère les groupes de transactions ayant exactement le même montant et des dates espacées de **2 jours ou moins**. Par défaut, les dépenses sont comparées avec les dépenses et les revenus avec les revenus. Les résultats sont présentés comme **doublons potentiels** avec les détails nécessaires pour ouvrir, modifier ou supprimer manuellement une transaction; aucune suppression n’est automatique.

Le bouton **Vérifier les non conciliées du mois** affiche toutes les transactions confirmées encore à concilier pour le mois choisi, regroupées par compte ou carte. Cette vue sert de liste de contrôle de fin de mois et signale aussi les transactions appartenant à un groupe de doublons potentiels. Pour un compte bancaire, une transaction peut être marquée **Vu** directement depuis cette vérification.

### Importer

L’onglet **Exporter** contient aussi la zone d’importation. Les formats reconnus sont :

- le CSV original de Spendee;
- le CSV exporté par JF Apps;
- le JSON exporté par JF Apps.

Avant l’importation, l’application présente le nombre de transactions valides, les transactions déjà importées, les doublons possibles, les catégories, les étiquettes, les modes de paiement et, pour un JSON V1.6, les lignes du budget global détectées.

Les catégories, étiquettes et modes de paiement absents sont créés automatiquement. Les lignes de budget présentes dans une sauvegarde JSON V1.6 peuvent être restaurées.

Pour les exports Spendee contenant un horodatage UTC, la date est convertie selon le fuseau **America/Toronto**, adapté au Québec.

### Exporter

L’onglet **Exporter** produit un fichier CSV pour Excel et un fichier JSON de sécurité.

Les exportations contiennent notamment :

- le mode de paiement;
- le statut de conciliation;
- la date de conciliation;
- l’indicateur **Hors budget**;
- la source et la clé d’importation;
- l’indication qu’un mouvement est un paiement de carte lié;
- le compte bancaire de départ et la carte destinataire.

La sauvegarde JSON comprend aussi les lignes du **Budget global**, les réglages de visibilité des KPI, les paramètres des modes de paiement, y compris la limite d’une marge de crédit, ainsi que les données des paiements de cartes liés.

### Versions

La version de l’application apparaît près de son nom. Le Portail contient aussi une page **Nouveautés et versions**.
""",
    },
    {
        "title": "Journal de pression — V1.2.1",
        "icon": "monitor_heart",
        "caption": "Saisie, moyennes, rappels et notifications privées",
        "keywords": (
            "pression artérielle systolique diastolique pouls "
            "date heure appareil privé note historique pdf rapport "
            "aucune donnée courriel csv json import export "
            "sauvegarde doublon données moyenne intervalle "
            "notification push appareil heure limite rappel matin soir rapport"
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

Il est possible d’enregistrer plus de deux mesures dans une même journée. Toutes les mesures peuvent être incluses dans le calcul des moyennes de l’intervalle choisi. Cette version ne présente pas encore de graphique.

### Horaires et rappel sur le Portail

L’onglet **Rappel** permet de définir :

- une date de début;
- une date de fin;
- l’activation ou la désactivation de l’avis;
- une ou plusieurs prises quotidiennes;
- un nom et une plage horaire pour chaque prise;
- une heure de notification facultative pour chaque prise.

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

### Avis de rappel sur le Portail

Lorsque les rappels sont actifs et qu’une prise reste à faire dans la journée, le Portail affiche un avis **Journal de pression** avec le bouton **Saisir maintenant**.

La version V1.1.1 corrige le chargement de cet avis après l’ouverture du Portail. Les plages horaires, l’ordre chronologique des prises et la règle voulant que toute mesure de la journée compte comme une prise complétée demeurent inchangés.

### Saisie rapide depuis le Portail

Le bouton **Saisir maintenant** ouvre directement l’onglet **Saisie**. La date et l’heure de l’appareil sont proposées et le champ **Systolique** reçoit automatiquement le curseur.

Le bouton **Enregistrer et revenir au Portail** permet d’enregistrer la mesure puis de retourner immédiatement à la page d’accueil.

### Notifications sur l’appareil

Le Journal peut aussi utiliser les notifications **Web Push** de la PWA.

Dans l’onglet **Rappel**, chaque prise possède une option **Notification sur l’appareil** et une heure **Avis appareil à**. Lorsque cette heure est atteinte, le serveur vérifie d’abord combien de mesures ont réellement été enregistrées dans la journée.

La règle reste la même que pour le Portail : les mesures sont associées chronologiquement aux prises prévues. Par exemple, si la première mesure de la journée existe déjà, aucune notification n’est envoyée pour la première prise, même si cette mesure a été enregistrée hors de sa plage horaire.

L’activation se fait séparément avec **Activer sur cet appareil**. Chaque téléphone, tablette ou ordinateur peut donc être activé ou désactivé indépendamment.

Le fuseau horaire de l’appareil est conservé avec son abonnement afin que l’heure de notification reste une heure locale.

La notification ne contient aucune valeur médicale. Le texte utilisé est volontairement générique :

**Journal de pression — Une mesure est prévue.**

Le navigateur doit autoriser les notifications et la PWA doit pouvoir utiliser les notifications Web Push. Sur les appareils où cette fonction n’est pas offerte, le rappel visuel du Portail continue de fonctionner normalement.

### Historique et moyennes

L’onglet **Historique** permet de choisir une plage de dates, puis de consulter, modifier ou supprimer les mesures du compte connecté.

Chaque fiche affiche :

- l’heure;
- la pression systolique et diastolique;
- le pouls;
- la note facultative.

Pour la même plage de dates, un encadré **Moyennes de l’intervalle** affiche :

- la moyenne de la pression systolique;
- la moyenne de la pression diastolique;
- la moyenne du pouls;
- le nombre total de mesures utilisées.

Le calcul utilise toutes les mesures réellement enregistrées entre les deux dates inclusivement. Les journées sans mesure n’ajoutent aucune valeur fictive au calcul.

### Exportation et sauvegarde privée

L’onglet **Données** permet de produire deux formats :

- **CSV** : tableau simple destiné notamment à Excel;
- **JSON** : sauvegarde complète contenant les mesures et les plages de rappel.

Le CSV contient la date, l’heure, la pression systolique, la pression diastolique, le pouls et la note.

Le JSON conserve aussi :

- l’état du rappel;
- la période du rappel;
- le nombre de prises quotidiennes;
- le nom et les heures de chaque plage;
- l’activation et l’heure de notification de chaque prise.

Les fichiers appartiennent uniquement à l’utilisateur connecté. Ils doivent être conservés dans un emplacement privé.

### Importation contrôlée

L’onglet **Données** accepte les fichiers CSV et JSON produits par JF Apps.

Avant l’importation, l’application affiche :

- le nombre de mesures valides;
- les mesures déjà présentes;
- les mesures différentes ayant la même date et la même heure;
- les lignes invalides;
- un aperçu des mesures à ajouter.

Les doublons exacts sont toujours ignorés.

Une mesure différente ayant exactement la même date et la même heure est considérée comme un conflit possible. Elle est ignorée par défaut, mais l’utilisateur peut choisir de l’importer lorsqu’il s’agit réellement d’une seconde mesure.

Avec une sauvegarde JSON, une option permet aussi de remplacer les plages et réglages de rappel actuels. Cette option est désactivée par défaut.

### Rapport PDF

Dans **Rapport PDF**, inscrivez le **nom complet à imprimer**, puis choisissez la date de début et la date de fin.

Par défaut, le rapport affiche l’heure exacte de chaque mesure. L’option **Afficher « Matin / Soir » plutôt que l’heure exacte** permet de produire un rapport plus simple :

- une mesure prise avant 12 h est affichée **Matin**;
- une mesure prise à partir de 12 h est affichée **Soir**.

Cette option modifie uniquement la présentation du PDF. L’heure exacte demeure enregistrée dans le Journal et reste disponible dans l’historique, le CSV et la sauvegarde JSON. Les notes du rapport utilisent elles aussi **Matin** ou **Soir** lorsque cette option est activée.

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
        "title": "Personnages JDR — V1.2.0",
        "icon": "casino",
        "caption": "Races, équipement, poids et feuille Pathfinder / Ravenloft",
        "keywords": (
            "jdr personnage ravenloft pathfinder feuille force "
            "dextérité constitution intelligence sagesse charisme "
            "classe armure initiative sauvegarde peur horreur folie "
            "compétence attaque points vie audit vérification calcul "
            "race héritage traits raciaux équipement armure bouclier "
            "poids encombrement charge légère moyenne lourde vitesse"
        ),
        "content": """
### Données privées et plusieurs personnages

Chaque personnage appartient uniquement à l’utilisateur connecté. Il n’est pas partagé avec une famille ou un autre compte pendant cette version.

L’utilisateur peut créer plusieurs personnages, passer de l’un à l’autre et supprimer un personnage avec confirmation.

### Identité

L’onglet **Identité** permet notamment de saisir :

- le nom du personnage et du joueur;
- la campagne;
- la classe et le niveau;
- la race, l’héritage ou la sous-race;
- l’alignement et la divinité;
- la catégorie de taille;
- l’âge, le genre, la taille physique et le poids du personnage;
- les yeux, les cheveux et la peau;
- les points d’expérience.

### Race principale et profil racial

Le champ **Race principale** est une liste déroulante recherchable. Elle contient :

- Humain;
- Nain;
- Elfe;
- Gnome;
- Demi-elfe;
- Demi-orque;
- Halfelin;
- Autre / personnalisée.

Le profil racial peut alimenter :

- le type et les sous-types;
- la catégorie de taille;
- la vitesse de base;
- les sens et la vision;
- les langues;
- un résumé des ajustements raciaux de caractéristiques;
- le multiplicateur de capacité de charge;
- le statut bipède ou quadrupède;
- les exceptions de vitesse sous armure ou sous encombrement.

Le champ **Héritage / sous-race** demeure facultatif. Les **traits raciaux alternatifs** peuvent être inscrits librement, en précisant idéalement quel trait standard est remplacé.

### Changement de race sécuritaire

Lorsqu’une race de base est choisie, l’application affiche un aperçu des changements suggérés avant de les appliquer.

L’utilisateur peut :

- annuler le changement;
- conserver ses valeurs actuelles;
- appliquer le profil proposé.

Les six scores de caractéristiques ne sont jamais modifiés silencieusement. Le résumé des ajustements raciaux sert de référence et permet de conserver les personnages déjà créés ou les règles particulières d’une campagne Ravenloft.

### Caractéristiques et combat

L’onglet **Combat** contient les six caractéristiques :

- FOR — Force;
- DEX — Dextérité;
- CON — Constitution;
- INT — Intelligence;
- SAG — Sagesse;
- CHA — Charisme.

Le modificateur est calculé automatiquement. Un score temporaire peut remplacer le score normal pour représenter un effet magique, une maladie ou une autre modification.

Les six cartes restent compactes. Les champs de **Combat et défenses** conservent leurs petits libellés, mais les valeurs numériques sont maintenant affichées plus gros afin de faciliter la lecture sur ordinateur et téléphone.

La feuille calcule notamment :

- la CA totale;
- la CA de contact;
- la CA lorsque le personnage est pris au dépourvu;
- l’initiative;
- le BMO / CMB;
- le DMD / CMD;
- la vitesse finale après l’armure et l’encombrement.

Les anciens champs **Armure manuel**, **Bouclier manuel** et **Pénalité d’armure manuelle** demeurent disponibles pour les personnages existants et les situations personnalisées. Lorsqu’un équipement fournit le même type de bonus, l’application retient la valeur applicable sans additionner deux fois deux sources incompatibles du même type.

### Équipement

Le nouvel onglet **Équipement** permet d’enregistrer :

- des armures;
- des boucliers;
- des armes;
- d’autres objets et possessions.

Chaque entrée peut contenir :

- un nom;
- un type;
- une quantité;
- un poids unitaire;
- une valeur;
- une note;
- un état **Transporté**;
- un état **Équipé**.

Pour les armures et boucliers, des renseignements supplémentaires sont disponibles :

- catégorie d’armure;
- bonus d’armure ou de bouclier;
- bonus d’altération;
- bonus maximal de Dextérité;
- pénalité d’armure aux tests;
- risque d’échec des sorts profanes;
- réduction de vitesse;
- vitesse personnalisée;
- maîtrise requise.

Une seule armure principale et un seul bouclier peuvent normalement contribuer aux calculs en même temps. Équiper une autre protection du même type retire automatiquement l’ancienne contribution.

### Effets automatiques de l’équipement

Une armure ou un bouclier équipé peut alimenter automatiquement :

- la CA totale;
- la CA lorsque le personnage est pris au dépourvu;
- le bonus maximal de Dextérité applicable à la CA;
- la pénalité d’armure aux compétences;
- la vitesse;
- le multiplicateur de course.

La CA de contact n’inclut normalement ni le bonus d’armure ni le bonus de bouclier. La décomposition des calculs indique les valeurs effectivement retenues.

### Poids et encombrement

Le poids total transporté est calculé avec :

```text
Quantité × poids unitaire de chaque objet transporté
```

Le résumé affiche :

- le poids total transporté;
- la charge légère maximale;
- la charge moyenne maximale;
- la charge lourde maximale;
- la charge actuelle;
- le poids restant avant le prochain seuil;
- la capacité pour soulever ou pousser;
- la vitesse finale;
- le multiplicateur de course.

Les seuils sont calculés à partir de la Force effective. Ils tiennent aussi compte de la taille, du statut bipède ou quadrupède et d’un multiplicateur racial ou personnalisé.

Une charge légère n’impose pas de restriction. Une charge moyenne ou lourde peut réduire :

- la vitesse;
- le bonus maximal de Dextérité;
- certains tests;
- la course.

Lorsqu’une armure et la charge imposent toutes deux une restriction, l’application utilise la valeur la plus défavorable sans additionner deux fois les pénalités d’armure et d’encombrement.

### Vitesse et exceptions raciales

La vitesse finale est décomposée à partir de :

- la vitesse raciale ou vitesse de base;
- la restriction de l’armure;
- la restriction de la charge;
- une éventuelle vitesse personnalisée;
- les exceptions raciales ou de campagne.

Le profil du Nain active notamment les exceptions permettant de conserver sa vitesse sous certaines armures ou charges. Les cases de dérogation demeurent modifiables afin d’accommoder les races personnalisées, les capacités de classe et les campagnes Ravenloft.

### BMO / CMB et DMD / CMD

Les champs et les résultats de **Combat et défenses** restent visibles directement dans la feuille. Les explications détaillées sont regroupées avec le bouton **Règles de calcul**.

Cette rubrique présente :

- la formule du BMO/CMB;
- la formule du DMD/CMD;
- l’utilisation de la Dextérité pour une créature Très petite ou plus petite;
- les bonus d’esquive et autres bonus applicables;
- l’application des pénalités négatives de Divers CA.

### Règles de calcul intégrées

Le bouton **Règles de calcul** ouvre une aide détaillée regroupant :

- les modificateurs de caractéristiques;
- la CA totale, la CA de contact et la CA pris au dépourvu;
- l’initiative;
- le BMO/CMB et le DMD/CMD;
- Vigueur, Réflexes, Volonté, Peur, Horreur et Folie;
- les compétences;
- les bonus d’attaque;
- l’équipement, le poids et la vitesse.

Chaque rubrique présente une formule générale et, lorsque possible, un exemple calculé à partir du personnage actuel.

La rubrique Compétences contient aussi l’exemple de référence **Dressage — Handle Animal** et les tests internes des calculs.

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

La liste de départ utilise les compétences de Pathfinder 1re édition. Pour chaque compétence, l’utilisateur peut modifier :

- le nom français et le nom anglais;
- la caractéristique associée;
- les rangs entiers;
- le modificateur divers;
- le statut de compétence de classe;
- la formation requise;
- l’application de la pénalité d’armure.

Une compétence est considérée comme possédée lorsqu’au moins 1 rang y est investi. Une compétence de classe possédée reçoit automatiquement le bonus de +3.

Les champs **Carac.**, **Rangs** et **Divers**, ainsi que les cases **Classe**, **Formation**, **Armure** et **×2**, restent regroupés sur une ligne lorsque la largeur le permet.

### Vérification générale de la feuille

La section **Compétences** présente un encadré **Vérification des calculs**.

Il peut signaler :

- une pénalité d’armure inscrite avec un signe positif;
- un possible double bonus de compétence de classe;
- une compétence exigeant une formation sans rang;
- l’option de pénalité d’armure ×2 sans l’option Armure.

Les tests de référence comprennent notamment :

- un score de caractéristique de 7 donnant un modificateur de −2;
- Dressage / Handle Animal : Charisme −2 + rangs 1 + classe 3 + divers 0 = +2;
- aucun bonus de compétence de classe lorsque les rangs sont à zéro;
- l’utilisation de la Dextérité pour le BMO/CMB d’une créature Très petite;
- un exemple complet de DMD/CMD.

Cette vérification ne modifie jamais automatiquement les données.

### Attaques

L’utilisateur peut enregistrer autant d’attaques que nécessaire avec :

- le nom;
- la caractéristique utilisée;
- les bonus magique et divers;
- les dégâts;
- le critique;
- la portée;
- le type;
- les notes;
- les munitions actuelles et maximales.

Le bonus total combine le bonus de base à l’attaque, le modificateur de caractéristique, la taille, la magie et les modificateurs divers.

### Limites de cette version

La section Équipement automatise d’abord les armures, les boucliers, le poids et l’encombrement. Les armes et possessions sont enregistrées, mais leurs effets spéciaux ne sont pas tous interprétés automatiquement.

Les dons, capacités spéciales, sorts, impression PDF, progression avancée et groupes de campagne restent prévus pour des versions ultérieures.
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

Par exemple, Café, Céréales et Concombre sont classés selon leurs lettres normales, sans repousser les mots accentués à la fin. Les ligatures courantes sont aussi normalisées : Œufs est trié comme Oeufs. L’orthographe originale reste affichée.
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
