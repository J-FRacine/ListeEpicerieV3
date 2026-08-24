from __future__ import annotations

PORTAL_VERSION = "1.3.0"

APP_LABELS = {
    "portal": "Portail JF Apps",
    "grocery": "Liste d’épicerie",
    "blood_pressure": "Journal de pression",
    "finances": "Finances",
    "rpg": "Personnages JDR",
    "feedback": "Commentaires et suggestions",
}

APP_VERSIONS = {
    "portal": PORTAL_VERSION,
    "grocery": "1.1.2",
    "blood_pressure": "1.2.1",
    "finances": "1.10.0",
    "rpg": "1.2.0",
    "feedback": "1.0.0",
}

RELEASE_NOTES = [
    {
        "app_key": "finances",
        "version": "1.10.0",
        "date": "2026-08-24",
        "title": "Finances — Budget fixe, capacité variable et financements",
        "summary": (
            "Le Tableau devient le suivi des dépenses variables du mois tandis que "
            "le Budget calcule la capacité disponible après les dépenses fixes."
        ),
        "changes": [
            "Le Tableau met en avant Reste par paie, Disponible ce mois selon le nombre réel de paies, Dépenses réalisées, À venir, Total prévu variable et Reste disponible ce mois.",
            "Le bloc KPI revenus est retiré du Tableau sans supprimer les revenus des données, récurrences, historiques ni calculs du Budget.",
            "Les KPI de dépenses affichent une ligne Total des KPI affichés; le rappel sur les étiquettes multiples est conservé.",
            "Les dépenses fixes liées à une récurrence Budget sont exclues du suivi variable du Tableau afin de ne pas consommer deux fois la capacité calculée.",
            "Chaque poste Budget peut avoir une date de début et une date de fin facultatives; les mois passés conservent les montants qui leur étaient applicables.",
            "Une nouvelle période d’un poste Budget peut être créée sans écraser l’ancienne; les chevauchements identiques sont bloqués par défaut et peuvent être autorisés explicitement.",
            "Nouveau module Financements pour les programmes de magasins et les achats en versements sur carte, avec ou sans intérêts et frais.",
            "Les plans déjà en cours peuvent être saisis avec montant initial, versements effectués, solde restant et prochaine échéance sans recréer automatiquement les anciennes mensualités.",
            "Chaque versement futur est une vraie dépense prévue, catégorisable et étiquetable, incluse dans les KPI et le budget restant; le montant initial n’est pas compté une seconde fois.",
            "Les versements liés à une carte apparaissent sur cette carte et deviennent disponibles pour la conciliation lorsqu’ils sont confirmés.",
            "Aucun script SQL manuel ni nouvelle dépendance n’est requis.",
        ],
    },
    {
        "app_key": "portal",
        "version": "1.3.0",
        "date": "2026-08-24",
        "title": "JF Apps — sauvegarde globale en une action",
        "summary": (
            "Le Portail peut créer une seule archive privée regroupant les données "
            "de toutes les applications auxquelles le compte a accès."
        ),
        "changes": [
            "Nouveau bouton Sauvegarder toutes mes données dans le Portail.",
            "L’archive ZIP sépare clairement Liste d’épicerie, Finances, Journal de pression, Personnages JDR et commentaires lorsque ces modules sont accessibles.",
            "Un manifest conserve la date de sauvegarde et la version de chaque application.",
            "La Liste d’épicerie est sauvegardée famille par famille et uniquement pour les familles accessibles au compte.",
            "La restauration globale reste une évolution future contrôlée; cette version priorise l’export complet en une seule action.",
        ],
    },
    {
        "app_key": "grocery",
        "version": "1.1.2",
        "date": "2026-08-24",
        "title": "Liste d’épicerie — tri alphabétique accent-insensible renforcé",
        "summary": (
            "Le tri naturel déjà présent est conservé et renforcé pour que les accents "
            "et ligatures ne déplacent jamais les items dans la liste."
        ),
        "changes": [
            "Café est trié comme Cafe et Céréales comme Cereales, sans modifier l’orthographe affichée.",
            "Le tri reste insensible à la casse dans Items et Besoins.",
            "Les ligatures courantes comme Œ/Oe et Æ/Ae sont maintenant normalisées explicitement.",
        ],
    },
    {
        "app_key": "finances",
        "version": "1.9.0",
        "date": "2026-08-20",
        "title": "Finances — conciliation bancaire rapide et cartes plus souples",
        "summary": (
            "La vue Compte permet maintenant de concilier directement les mouvements bancaires, "
            "tandis que la conciliation des cartes conserve la sélection, ajoute le tri par date et gère les écarts justifiés sans les reporter."
        ),
        "changes": [
            "Dans Compte, chaque transaction d’un compte bancaire possède une case Vu : la cocher confirme au besoin la transaction et la marque conciliée avec la date du jour.",
            "Décocher Vu retire la conciliation sans effacer la transaction; les projections pures restent non cochables.",
            "La conciliation rapide par cases s’applique seulement aux comptes bancaires; les cartes de crédit conservent l’écran Conciliation par relevé.",
            "Dans Conciliation, l’ajout ou la modification d’une transaction ne vide plus les transactions déjà sélectionnées tant qu’elles demeurent admissibles pour la même carte.",
            "Un bouton Ajouter une transaction et un bouton Modifier sont disponibles directement pendant la conciliation.",
            "Le tri Date ascendante / Date descendante agit uniquement sur l’affichage et conserve la sélection en cours.",
            "La sélection reste aussi conservée lors d’un filtre ou d’un rafraîchissement; une transaction devenue inadmissible est retirée avec un avis.",
            "La conciliation d’une carte utilise maintenant le dernier relevé finalisé comme solde de référence : solde précédent + mouvements sélectionnés = solde attendu.",
            "Lorsqu’une différence existe, elle peut être clôturée comme écart justifié avec une explication; le solde réel du relevé devient alors la nouvelle référence et l’écart ne revient pas au relevé suivant.",
            "Une option Reporter l’écart conserve au contraire le solde attendu comme référence afin que la différence demeure à résoudre plus tard.",
            "L’explication d’un écart justifié est conservée uniquement dans l’historique de la séance de conciliation et ne crée pas de transaction budgétaire ni de KPI.",
            "Aucun script SQL manuel ni nouvelle dépendance n’est requis.",
        ],
    },
    {
        "app_key": "finances",
        "version": "1.8.0",
        "date": "2026-08-11",
        "title": "Finances — paiements de cartes liés et Tableau plus compact",
        "summary": (
            "Les paiements de cartes peuvent maintenant relier un compte bancaire à une carte de crédit, "
            "l’Historique indique clairement les mouvements programmés et le détail des transactions à venir est replié par défaut."
        ),
        "changes": [
            "Nouveau formulaire Paiement de carte : choix du compte bancaire de départ, de la carte destinataire, du montant et des dates de débit et de réception.",
            "Un paiement de carte crée un seul mouvement logique avec deux effets liés : sortie du compte bancaire et crédit sur la carte, automatiquement Hors budget.",
            "Le côté carte apparaît dans Conciliation comme un paiement reçu qui réduit le solde dû lorsque le paiement est confirmé.",
            "Modifier, confirmer ou supprimer un paiement lié met à jour les deux côtés ensemble; une conciliation existante doit d’abord être retirée avant modification ou suppression.",
            "Le rappel et l’indicateur Programmé s’appliquent au côté bancaire du paiement prévu.",
            "Dans l’Historique, le libellé court Programmé apparaît directement sur la ligne d’une transaction déjà programmée à la banque.",
            "Dans le Tableau, les trois montants Dépenses à venir, Revenus à venir et Effet net prévu restent visibles, tandis que les longues listes de détail sont repliées par défaut.",
            "Le détail des transactions à venir peut être ouvert au besoin avec un panneau extensible indiquant le nombre de dépenses et de revenus.",
            "Les sauvegardes JSON incluent les informations des paiements de cartes liés et le CSV identifie leur compte de départ et leur carte destinataire.",
            "Aucun script SQL manuel ni nouvelle dépendance n’est requis.",
        ],
    },
    {
        "app_key": "finances",
        "version": "1.7.0",
        "date": "2026-08-10",
        "title": "Finances — récurrences dynamiques, KPI configurables et marge de crédit",
        "summary": (
            "Les récurrences recalculent maintenant leurs prévisions, le Tableau peut être allégé "
            "par catégorie ou étiquette et la vue Compte prend en charge les marges de crédit."
        ),
        "changes": [
            "Une modification de date, montant ou fréquence d’une récurrence supprime et reconstruit ses occurrences prévues non confirmées.",
            "Lorsqu’une correction de récurrence crée une occurrence déjà passée, cette occurrence est remise À confirmer plutôt que d’être silencieusement inscrite comme transaction réalisée.",
            "Les transactions confirmées restent intactes afin de préserver l’historique réel.",
            "Une récurrence peut être supprimée en choisissant de supprimer ses transactions prévues ou de les conserver comme transactions indépendantes.",
            "Les postes Budget liés à une récurrence supprimée deviennent automatiquement indépendants.",
            "Dans Organisation, chaque catégorie et étiquette possède une case Tableau pour choisir si elle apparaît dans les KPI du Tableau de bord.",
            "Les réglages KPI existants sont activés par défaut après la mise à jour afin de ne rien masquer sans choix de l’utilisateur.",
            "Nouveau type de mode de paiement Marge de crédit avec solde utilisé de référence, limite facultative et crédit disponible.",
            "Dans une marge de crédit, une dépense augmente la dette et un remboursement la réduit; les transactions, récurrences et projections utilisent cette logique.",
            "La vue Compte affiche dette actuelle, plus haut prévu, dette de fin de mois et crédit disponible lorsque la limite est renseignée.",
            "Les transactions prévues dont la date est passée restent visibles dans la projection jusqu’à confirmation ou correction.",
            "Aucun script SQL manuel ni nouvelle dépendance n’est requis.",
        ],
    },
    {
        "app_key": "finances",
        "version": "1.6.2",
        "date": "2026-08-10",
        "title": "Finances — correctif de démarrage V1.6",
        "summary": (
            "Le démarrage du Portail est maintenant protégé contre une erreur "
            "de migration ou de notification Finances."
        ),
        "changes": [
            "Les migrations Finances ne peuvent plus empêcher le Portail entier de démarrer.",
            "L’initialisation des rappels Finances est déplacée dans la tâche de fond après le démarrage HTTP.",
            "Le lien Budget–Récurrence conserve sa validation applicative sans imposer de nouvelle contrainte SQL au démarrage.",
            "Si une migration Finances échoue encore, l’erreur exacte est affichée dans l’écran Finances et imprimée dans le journal.",
            "Toutes les fonctions de V1.6.1 sont conservées.",
        ],
    },
    {
        "app_key": "finances",
        "version": "1.6.1",
        "date": "2026-08-10",
        "title": "Finances — budget lié, transactions programmées et rappels",
        "summary": (
            "Les postes du Budget peuvent être liés aux récurrences et les transactions "
            "prévues peuvent être identifiées comme programmées à la banque et rappelées par notification."
        ),
        "changes": [
            "Lien facultatif entre un poste du Budget et une récurrence existante.",
            "Synchronisation optionnelle du montant et de la fréquence du Budget avec la récurrence liée.",
            "Nouvel indicateur Programmée à la banque pour les transactions prévues et les récurrences.",
            "Rappel Web Push facultatif le jour prévu, avec heure configurable et 09:00 par défaut.",
            "Les rappels de récurrence fonctionnent même si l’occurrence n’a pas encore été matérialisée dans l’Historique.",
            "Activation et désactivation des notifications directement dans l’onglet Compte; les appareils déjà autorisés pour Journal de pression sont réutilisés.",
            "Les transactions confirmées ne déclenchent plus leur rappel prévu.",
            "Compte, Historique et Récurrences affichent les indicateurs Programmée à la banque et Rappel.",
            "CSV et JSON conservent les nouveaux indicateurs des transactions; aucun script SQL manuel n’est requis.",
        ],
    },
    {
        "app_key": "finances",
        "version": "1.6.0",
        "date": "2026-08-10",
        "title": "Finances — compte bancaire et budget global",
        "summary": (
            "Ajout d’une vue de trésorerie avec solde courant et prévisionnel, "
            "d’un aperçu annuel et d’un budget mensuel / aux deux semaines."
        ),
        "changes": [
            "Nouvel onglet Compte avec solde de départ, solde actuel, plus bas prévu et solde de fin de mois.",
            "Liste chronologique des entrées et sorties avec recalcul du solde après chaque mouvement.",
            "Aperçu annuel des douze mois avec solde de fin et minimum prévu, chaque mois étant accessible directement.",
            "Réutilisation des modes de paiement de type Compte bancaire avec solde et date de référence comme point de départ.",
            "Nouvel onglet Budget pour planifier revenus et dépenses en montant mensuel ou aux deux semaines sur une base de 26 paies.",
            "Possibilité de remplacer le montant par paie calculé automatiquement par un montant personnalisé afin de conserver un coussin volontaire.",
            "Nouvelle option Hors budget pour les transferts, paiements de cartes et déplacements d’épargne : le mouvement peut affecter le compte sans être recompté dans les dépenses, revenus, KPI ou objectifs.",
            "Les récurrences peuvent mémoriser l’option Hors budget et la transmettre aux occurrences créées.",
            "Le Tableau affiche un résumé du compte bancaire lorsque celui-ci possède un solde de référence.",
            "CSV et JSON enrichis de l’indicateur Hors budget; la sauvegarde JSON comprend aussi les lignes du budget global.",
        ],
    },
    {
        "app_key": "blood_pressure",
        "version": "1.2.1",
        "date": "2026-08-10",
        "title": "Journal de pression — rapport Matin / Soir",
        "summary": (
            "Le rapport PDF peut maintenant remplacer les heures exactes "
            "par les libellés Matin et Soir, sans modifier les mesures enregistrées."
        ),
        "changes": [
            "Nouvelle option dans Rapport PDF pour afficher Matin / Soir plutôt que l’heure exacte.",
            "Mode Heure exacte conservé par défaut pour préserver le comportement actuel.",
            "En mode Matin / Soir, une mesure avant 12 h est libellée Matin et une mesure à partir de 12 h est libellée Soir.",
            "Les notes du rapport utilisent le même libellé Matin / Soir lorsque l’option est activée.",
            "Les heures originales demeurent enregistrées et restent visibles dans l’historique et les exportations.",
        ],
    },
    {
        "app_key": "finances",
        "version": "1.5.0",
        "date": "2026-08-09",
        "title": "Finances — KPI cliquables et création rapide",
        "summary": (
            "Les catégories et étiquettes du Tableau ouvrent maintenant "
            "leurs transactions et peuvent être créées directement pendant la saisie."
        ),
        "changes": [
            "Noms de catégories et d’étiquettes cliquables dans les KPI.",
            "Fenêtre de détail avec Réalisé, À venir et Total prévu.",
            "Transactions réelles accessibles depuis le détail; projections de récurrence laissées en consultation.",
            "Option Ajouter une catégorie directement dans la Saisie rapide.",
            "Création facultative d’une sous-catégorie sous une catégorie principale.",
            "Option Ajouter une étiquette sans perdre les étiquettes déjà sélectionnées.",
            "Détection des doublons évidents en ignorant la casse, les accents et les espaces superflus.",
        ],
    },
    {
        "app_key": "blood_pressure",
        "version": "1.2.0",
        "date": "2026-08-09",
        "title": "Journal de pression — moyennes et notifications",
        "summary": (
            "Ajout des moyennes sur une plage de dates et des notifications "
            "Web Push lorsqu’une prise attendue n’est toujours pas complétée."
        ),
        "changes": [
            "Moyenne systolique, diastolique et du pouls pour l’intervalle choisi.",
            "Nombre de mesures utilisées dans le calcul affiché avec les moyennes.",
            "Heure de notification configurable pour chaque prise quotidienne.",
            "Activation et désactivation des notifications séparément sur chaque appareil.",
            "Vérification serveur des mesures avant tout envoi afin d’éviter les avis inutiles.",
            "Notification volontairement générique sans valeur médicale.",
            "Fuseau horaire enregistré par appareil pour respecter les heures locales.",
            "Sauvegarde JSON enrichie des heures et options de notification.",
        ],
    },
    {
        "app_key": "rpg",
        "version": "1.2.0",
        "date": "2026-08-04",
        "title": "Personnages JDR — races, équipement et encombrement",
        "summary": (
            "Ajout des profils raciaux, d’une section Équipement "
            "et du calcul automatique du poids, de la vitesse et des protections."
        ),
        "changes": [
            "Race principale dans une liste déroulante recherchable avec les sept races de base Pathfinder et un profil personnalisé.",
            "Héritage, sous-race, traits alternatifs, type, sous-types, vision, langues et ajustements raciaux.",
            "Prévisualisation sécurisée avant d’appliquer un profil racial, sans modifier silencieusement les caractéristiques.",
            "Nouvel onglet Équipement pour les armures, boucliers, armes et possessions.",
            "Une seule armure et un seul bouclier équipés contribuent automatiquement aux calculs.",
            "Bonus d’armure, de bouclier et d’altération intégrés à la CA.",
            "Bonus maximal de Dextérité, pénalité d’armure et vitesse issus de l’équipement.",
            "Calcul du poids total transporté selon la quantité et le poids de chaque objet.",
            "Seuils de charge légère, moyenne et lourde selon la Force, la taille et le type bipède ou quadrupède.",
            "Vitesse finale calculée avec l’armure, la charge et les exceptions raciales.",
            "Application de la restriction la plus défavorable entre armure et charge, sans doubler les pénalités.",
            "Valeurs numériques de Combat et défenses plus grandes et plus faciles à lire.",
            "Règles de calcul enrichies d’une décomposition de l’équipement, du poids et de la vitesse.",
        ],
    },
    {
        "app_key": "rpg",
        "version": "1.1.1",
        "date": "2026-08-04",
        "title": "Personnages JDR — aide de combat déplacée",
        "summary": (
            "Les formules BMO/CMB et DMD/CMD sont maintenant "
            "regroupées uniquement dans la fenêtre Règles de calcul."
        ),
        "changes": [
            "Retrait du grand encadré explicatif dans Combat et défenses.",
            "Conservation des formules BMO/CMB et DMD/CMD dans Règles de calcul.",
            "Conservation de l’explication sur les bonus d’esquive et les pénalités de CA.",
            "Interface Combat et défenses plus compacte et plus directe.",
            "Aucun calcul ni aucune donnée de personnage n’est modifié.",
        ],
    },
    {
        "app_key": "blood_pressure",
        "version": "1.1.0",
        "date": "2026-08-04",
        "title": "Journal de pression — sauvegarde privée et importation",
        "summary": (
            "Ajout des exportations CSV et JSON, de l’importation "
            "contrôlée et de la détection des doublons."
        ),
        "changes": [
            "Nouvel onglet Données pour importer et exporter les mesures.",
            "Export CSV compatible avec Excel.",
            "Sauvegarde JSON complète incluant les plages et réglages de rappel.",
            "Prévisualisation avant toute importation.",
            "Détection des mesures déjà présentes.",
            "Détection des mesures différentes à la même date et à la même heure.",
            "Importation facultative des plages de rappel depuis une sauvegarde JSON.",
            "Onglets horizontaux adaptés au téléphone.",
            "Remplacement des minuteries de montage par des tâches contrôlées.",
        ],
    },
    {
        "app_key": "rpg",
        "version": "1.1.0",
        "date": "2026-08-04",
        "title": "Personnages JDR — vérification des calculs Pathfinder",
        "summary": (
            "Ajout d’un audit visible de la feuille et de tests "
            "de référence pour les principaux calculs."
        ),
        "changes": [
            "Vérification automatique des compétences et des pénalités d’armure.",
            "Avertissement lorsqu’un bonus de classe +3 semble aussi inscrit dans Divers.",
            "Avertissement pour une compétence exigeant une formation sans rang.",
            "Contrôle du réglage ×2 de la pénalité d’armure.",
            "Tests de référence intégrés pour les caractéristiques, compétences, BMO/CMB et DMD/CMD.",
            "Exemple explicite Dressage — Handle Animal donnant un total de +2.",
            "Décomposition visible des calculs conservée dans l’interface compacte.",
        ],
    },
    {
        "app_key": "finances",
        "version": "1.4.1",
        "date": "2026-08-03",
        "title": "Finances — correction du menu sur téléphone",
        "summary": (
            "Les onglets du sous-menu Finances ne se chevauchent "
            "plus sur les écrans étroits."
        ),
        "changes": [
            "Onglets non compressibles avec largeur adaptée à leur libellé.",
            "Défilement horizontal tactile du sous-menu sur téléphone.",
            "Icône et texte placés sur une même ligne pour réduire la hauteur.",
            "Flèches de navigation affichées lorsque tous les onglets ne tiennent pas.",
            "Aucun changement aux transactions, récurrences ou conciliations.",
        ],
    },
    {
        "app_key": "portal",
        "version": "1.2.1",
        "date": "2026-08-03",
        "title": "Portail JF Apps — restauration de la page principale",
        "summary": (
            "Correction d’une route NiceGUI manquante qui provoquait "
            "une page 404 après le déploiement."
        ),
        "changes": [
            "Restauration de la route principale / du Portail.",
            "Les adresses / et /?tab=items sont de nouveau reconnues.",
            "Aucune donnée ni fonction d’application n’est modifiée.",
        ],
    },
    {
        "app_key": "grocery",
        "version": "1.1.1",
        "date": "2026-08-03",
        "title": "Liste d’épicerie — stabilité du Mode courses",
        "summary": (
            "Correction d’un arrêt du service causé par des minuteries "
            "NiceGUI dont la page avait déjà été fermée."
        ),
        "changes": [
            "Remplacement des minuteries liées à l’interface par des tâches contrôlées.",
            "Arrêt automatique de l’actualisation du Mode courses lorsque la page est quittée.",
            "Protection de la période d’annulation dans Besoins après navigation.",
            "Conservation du bouton d’actualisation manuelle dans le Mode courses.",
        ],
    },
    {
        "app_key": "portal",
        "version": "1.2.0",
        "date": "2026-08-03",
        "title": "JF Apps — correction mobile et navigation simplifiée",
        "summary": (
            "Refonte de l’en-tête sur téléphone et simplification "
            "de la navigation inférieure de la liste d’épicerie."
        ),
        "changes": [
            "En-tête mobile compact avec logo, nom de l’application, version, Portail et menu Plus.",
            "Commentaires, Aide, Compte, Nouveautés, Installer et Déconnexion regroupés dans le menu mobile.",
            "Indicateur de commentaires non lus conservé sur le menu Plus.",
            "Suppression du bouton Portail redondant dans la navigation inférieure de l’épicerie.",
            "Navigation inférieure de l’épicerie ramenée à une seule ligne.",
            "Versions et nouveautés des applications centralisées.",
        ],
    },
    {
        "app_key": "grocery",
        "version": "1.1.0",
        "date": "2026-08-03",
        "title": "Liste d’épicerie — tri naturel et catégories facultatives",
        "summary": (
            "Le tri ignore maintenant les accents et chaque famille "
            "peut choisir d’utiliser ou non les catégories."
        ),
        "changes": [
            "Tri alphabétique insensible aux accents et à la casse.",
            "Café, Céréales et leurs équivalents sans accents sont classés naturellement.",
            "Option Utiliser les catégories configurable par famille.",
            "Les catégories et associations existantes sont conservées lorsqu’elles sont masquées.",
            "Items, Besoins et Mode courses se regroupent uniquement par magasin lorsque les catégories sont désactivées.",
            "Le bouton Organisation devient Magasins dans la navigation lorsque les catégories sont désactivées.",
        ],
    },
    {
        "app_key": "finances",
        "version": "1.4.0",
        "date": "2026-08-03",
        "title": "Finances — réalisé, à venir et total prévu",
        "summary": (
            "Le Tableau projette les récurrences et présente les "
            "transactions postdatées du mois affiché."
        ),
        "changes": [
            "Projection des dépenses et revenus récurrents jusqu’à la fin du mois affiché.",
            "Transactions postdatées séparées des montants réalisés.",
            "Totaux Dépenses à venir, Revenus à venir et Effet net prévu.",
            "Liste des transactions à venir avec date, description et mode de paiement.",
            "KPI par catégorie et étiquette avec Réalisé, À venir et Total prévu.",
            "KPI distincts pour les dépenses et les revenus.",
            "Noms longs tronqués avec consultation du nom complet.",
            "Les objectifs mensuels excluent désormais les transactions postdatées du réalisé.",
        ],
    },
    {
        "app_key": "portal",
        "version": "1.1.0",
        "date": "2026-08-03",
        "title": "JF Apps — navigation et identité visuelle communes",
        "summary": (
            "Uniformisation du Portail et des applications avec un en-tête "
            "commun, un accès permanent au Portail et le logo comme icône."
        ),
        "changes": [
            "En-tête commun dans le Portail, l’épicerie, le Journal de pression, Finances et Personnages JDR.",
            "Bouton Portail toujours visible dans toutes les applications, y compris le mode Courses.",
            "Accès harmonisés à Commentaires, Manuel, Mon compte, Nouveautés et Déconnexion.",
            "Versions affichées de façon cohérente dans les en-têtes et les cartes du Portail.",
            "Onglets et menus internes harmonisés sur ordinateur et téléphone.",
            "Logo JF Apps utilisé comme favicon, icône PWA et repère visuel de navigation.",
            "Largeur et espacements communs pour mieux utiliser les écrans larges.",
            "Manuel et page Nouveautés mis à jour en même temps.",
        ],
    },
    {
        "app_key": "finances",
        "version": "1.3.0",
        "date": "2026-07-30",
        "title": "Finances — soldes prévus et conciliation par relevé",
        "summary": (
            "Ajout des soldes cumulatifs par mode de paiement, "
            "des séances de conciliation et de leur historique."
        ),
        "changes": [
            "Solde prévu cumulatif par mode de paiement, sans remise à zéro mensuelle.",
            "Sélection multiple des transactions à concilier par relevé.",
            "Solde du relevé, date de relevé, date de paiement et différence conservés.",
            "Historique des séances avec annulation complète ou retrait d’une transaction.",
            "Ajustement initial configurable par mode de paiement.",
            "Remboursements et revenus réduisant le solde prévu.",
            "Attribution en lot d’un mode aux transactions non classées.",
            "Type de mode, jours habituels de relevé et de paiement et notes.",
            "Export JSON enrichi de l’historique des conciliations.",
        ],
    },
    {
        "app_key": "finances",
        "version": "1.2.0",
        "date": "2026-07-30",
        "title": "Finances — paiements et conciliation",
        "summary": (
            "Ajout des modes de paiement, de la conciliation mensuelle, "
            "des KPI par catégorie et étiquette et d’un historique structuré."
        ),
        "changes": [
            "Modes de paiement configurables et réordonnables.",
            "Mode de paiement par transaction et par récurrence.",
            "Statut À concilier ou Conciliée avec date facultative.",
            "Filtres et résumé mensuel de conciliation.",
            "Revenus placés dans une colonne distincte sur grand écran.",
            "Montants alignés à droite dans l’historique et les KPI.",
            "KPI mensuels par catégorie et par étiquette.",
            "Importations et exportations enrichies des données de paiement.",
        ],
    },
    {
        "app_key": "finances",
        "version": "1.1.0",
        "date": "2026-07-29",
        "title": "Finances — importation contrôlée",
        "summary": (
            "Ajout de l’importation CSV et JSON avec prévisualisation, "
            "création des catégories et détection des doublons."
        ),
        "changes": [
            "Importation directe des fichiers CSV de Spendee.",
            "Importation des CSV et JSON exportés par JF Apps.",
            "Prévisualisation avant l’ajout des transactions.",
            "Création automatique des catégories et étiquettes manquantes.",
            "Détection des transactions déjà importées et des doublons possibles.",
            "Conservation de clés d’importation dans les futures exportations.",
        ],
    },
    {
        "app_key": "finances",
        "version": "1.0.0",
        "date": "2026-07-28",
        "title": "Finances V1",
        "summary": (
            "Première version du suivi privé des dépenses variables, "
            "revenus, récurrences et objectifs mensuels."
        ),
        "changes": [
            "Saisie rapide compacte pour téléphone.",
            "Catégories, sous-catégories et étiquettes multiples.",
            "Dépenses et revenus récurrents paramétrables.",
            "Objectifs mensuels avec reports configurables.",
            "Historique compact et filtres.",
            "Exportations CSV et JSON.",
        ],
    },
]


def get_app_version(app_key):
    return APP_VERSIONS.get(str(app_key or "").strip())


def get_app_label(app_key):
    key = str(app_key or "").strip()
    return APP_LABELS.get(key, key or "JF Apps")


def version_label(app_key):
    version = get_app_version(app_key)
    return f"V{version}" if version else None
