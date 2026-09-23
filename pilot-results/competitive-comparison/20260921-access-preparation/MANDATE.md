# Reprise : exécuter la comparaison Arcade / Workato

Prompt préparé le **21 septembre 2026** pour une autre session dans
`/home/alacasse/projects/moraine`. Sa rédaction ne lance aucun essai.

## Mandat de la prochaine session

Je veux lancer le [plan de comparaison Arcade / Workato](../plans/agent-access-competitive-comparison.md).
Travaille en français et avance jusqu'au bilan des observations réalisables,
en respectant les prérequis et autorisations du plan. La question est de savoir
ce que les offres existantes couvrent déjà et où Moraine pourrait apporter une
valeur utile. Les particuliers et les entreprises restent des publics possibles.

Commence par la préparation concrète : vérification des prérequis, fiche par
offre, corpus fictif et supports de collecte locaux. Pour les essais externes,
utilise uniquement les comptes, connexions et dépenses déjà désignés et
autorisés dans cette session. Prépare le périmètre exact avant de demander
les autorisations manquantes; poursuis entre-temps les travaux indépendants.
Le lancement de ce prompt n'autorise pas une dépense, la création d'un compte,
une connexion OAuth ou un contact commercial non précisés. Ne redemande pas
une autorisation déjà donnée pour le même périmètre.

## Charger le contexte et reprendre au bon endroit

Après les consignes applicables et l'[index documentaire](../README.md), lis :

1. Le [plan maintenu](../plans/agent-access-competitive-comparison.md), source
   du protocole, de la matrice de droits et des critères S0–S6.
2. Le [rapport de revue indépendante](../../pilot-results/competitive-comparison/20260921-plan-review/REPORT.md)
   et sa [contre-revue finale](../../pilot-results/competitive-comparison/20260921-plan-review/REVIEW-v2.md).
3. La [note de prérequis](../research/agent-access-comparison-prerequisites.md),
   puis le [rapport de marché](../research/enterprise-agent-access-market.md).
4. L'[état Moraine](../status.md) et son [contrat](../pilot/interface.md) pour
   borner les comparaisons avec le pilote. Consulter la
   [preuve existante](../../pilot-results/codex-email/20260921-agent-access/REPORT.md)
   lorsque tu rapportes ses résultats.

Le plan a déjà été revu par un agent distinct : deux P2 et un P3 corrigés,
puis aucun constat résiduel. La section 8 du plan décrit cette revue achevée;
reprends à la préparation des essais, sans refaire le plan ou la revue.
La [capture v2](../../pilot-results/competitive-comparison/20260921-plan-review/PLAN-v2.md)
avait pour SHA-256
`24b480003e61d742b8bb24af7f9ecfa2580e84069f9f6e045a7ac79549eea497`.
Compare le plan courant à cette version; si le protocole a évolué, identifie
l'écart avant d'appliquer l'ancien verdict. Préserve les captures historiques.

Le checkout de référence était `29a883450f585fc6662e151de133559670fc5864`.
Lors de cette préparation, les recherches, le plan et sa revue étaient encore
locaux, non commités. Utilise le workspace existant et vérifie son état actuel;
préserve toutes les modifications présentes. Ne suppose pas qu'un clone du
dépôt distant contient ces documents ni les autorisations de cette session.

## Exécuter sans fausser la comparaison

1. Vérifie dans les sources officielles les conditions actuelles qui changent
   la faisabilité : éditions, accès aux fonctions, OAuth/SSO, restrictions
   Confluence, durée et fin d'essai, coûts. Remplis les fiches de prérequis du
   plan avec valeurs établies, inconnues et autorisations encore nécessaires.
   Aucun prix ou accès d'essai ancien ne doit devenir une permission implicite.
2. Prépare localement le corpus et la matrice de collecte. Une fois les
   prérequis réunis pour une offre, exécute S0–S6 dans son environnement
   autorisé. Garde Arcade et Workato même si l'un reste inaccessible; rapporte
   un blocage plutôt que de remplacer silencieusement un candidat.
3. Respecte les corrections de revue : identifiants de B seuls lors du contrôle
   croisé vers A; révocation de A préservant U et B, avec connexions distinctes
   admises; compte U ordinaire et édition Confluence adaptée au témoin D4.
   L'opérateur peut jouer les rôles du scénario; indique cette simulation.
4. Distingue observations directes, documentation, extensions nécessaires et
   prérequis bloquants. Applique les bornes d'effort et contrôles du plan.
   Le pilote Moraine reste une référence historique limitée; son développement
   et celui d'extensions concurrentes sont hors de ce mandat.
5. Conserve les preuves expurgées dans un nouveau dossier de campagne prévu
   par le plan, puis retire seulement les ressources créées pour cet essai.
   Applique les [règles documentaires](../documentation.md) : secrets et exports
   bruts privés hors Git, preuves antérieures préservées.

## Livrer

Produis le rapport, la matrice et le manifeste définis dans le plan. Le bilan
doit préciser ce qui a été réellement essayé chez chaque candidat, ce qui
reste bloqué et pourquoi, les frictions observées, les possibilités de
réutilisation et les différences encore hypothétiques pour Moraine.

Une comparaison partielle doit rester utile et explicitement partielle.
Présente les interventions restantes sous forme concrète, une décision
importante à la fois, sans déduire d'un blocage une faiblesse du produit.
Ne transforme pas un résultat technique en preuve de volonté de payer.
Termine par les liens vers les livrables et les limites de la campagne.
Le commit et le push restent hors de ce mandat.
