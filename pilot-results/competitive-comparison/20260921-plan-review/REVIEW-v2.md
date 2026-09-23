# Contre-revue indépendante — seconde version

Date : 21 septembre 2026. Même reviewer indépendant :
`/root/review_competitive_comparison_plan`. Compte rendu conservé par l'agent
principal; les références de lignes désignent [PLAN-v2.md](PLAN-v2.md).

## Verdict final du reviewer

**Plan prêt à proposer.** Les deux constats P2 et le constat P3 de la première
revue sont résolus. Aucun constat résiduel P1, P2 ou P3, ni régression nécessitant
une nouvelle révision. Ce verdict porte sur la qualité du protocole proposé;
il ne constitue ni autorisation d'exécution ni validation des offres.

SHA-256 effectivement calculé et revérifié :
`24b480003e61d742b8bb24af7f9ecfa2580e84069f9f6e045a7ac79549eea497`.
Le contenu est identique byte à byte au plan actif. HEAD demeure
`29a883450f585fc6662e151de133559670fc5864`.

## Séparation A/B — P2 résolu

Lignes 168 et 174–180. S2 impose les seuls identifiants de B pour viser le
point d'entrée ou sélecteur public associé à A, lorsque cette substitution
existe. Le refus attendu sur D2 est un contrôle explicite. La preuve serveur
doit rattacher la décision à la délégation de B; l'absence de substitution
exige justification et preuve équivalente. Sans contrôle applicable ou preuve
équivalente, la séparation demeure « non établie », même si les parcours
ordinaires passent. Le faux succès est traité sans recherche de vulnérabilités
ni utilisation des secrets de A.

## Révocation sélective — P2 résolu

Ligne 171. Le critère protège le résultat attendu : compte et droits source
de U inchangés, accès de B conservés, lectures de A interrompues. Une connexion
propre à A est admise lorsqu'elle matérialise sa délégation; une connexion
commune est préservée si elle existe. Nombre de connexions, consentements
supplémentaires et couche responsable restent observables. Le biais
architectural est retiré sans transformer un retrait global en succès.

Les dispositions de révocation restent aux lignes 182–190 : lectures nouvelles,
contexte ouvert et vide, contrôle de B, observation jusqu'à cinq minutes et
distinction entre révocation, expiration et panne. Les données déjà reçues
restent hors de la promesse de retrait.

## Prérequis Confluence — P3 résolu

Lignes 67–69, 111–116 et 166. U est ordinaire et distinct de O. Édition source,
durée d'essai, conditions de fin et de facturation sont à vérifier avant D4.
L'absence du prérequis bloque ce témoin séparément, sans empêcher les contrôles
indépendants dont les droits initiaux sont établis. S0 interdit d'attribuer un
refus à la passerelle sans référence source correspondante.

## Limites et vérifications

La relecture complète ne révèle pas de perte des garde-fous antérieurs.
Moraine reste une référence historique limitée. Les extensions ne deviennent
pas des succès observés du produit standard. Éditions inaccessibles et preuves
insuffisantes restent distinctes des écarts fonctionnels. Le temps est borné;
les résultats ne tranchent ni marché visé ni volonté de payer.

Les inconnues restantes sont celles que l'essai doit résoudre : disponibilité
effective des fonctions, délégations distinctes, visibilité des traces et coût
du parcours. Elles permettent un résultat partiel exploitable sans imposer
d'infrastructure disproportionnée.

Vérifications déclarées : lecture intégrale de v2, comparaison avec v1,
identité avec le plan actif, empreintes des deux captures, HEAD et
`git diff --check` sans erreur. V1 inchangée. Aucun fichier modifié, essai
produit, test métier ou nouvelle consultation externe. Le rapport v1 n'a pas
été réécrit.
