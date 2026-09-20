# Coordination des prochains travaux Moraine

Date : 20 septembre 2026. Coordinateur : tâche « Évaluer les prochaines étapes ».
Base examinée : `b63590cc02dbcb31859aeb683f4f71314beeb775`.
Statut : les trois lots sont livrés et committés sur leurs branches dédiées,
après revues et corrections. Les trois lots sont intégrés dans le checkout
principal; validation combinée et revues consignées dans le
rapport d’intégration. A : 96 tests; C : 13 tests et sonde indépendante de 13 824 cas.
B reste un contrat proposé et revu, sans acceptation produit.
Après cette validation, l'utilisateur a demandé « Commit et pousse tout ça » :
commit d'intégration et publication de `master` et des branches A/B/C autorisés.

L’intégration publiée est `f4350fe37d285598ebe5ef9e3253ac2af12e3b35`.
Ce document conserve l’historique de ces lots. Le laboratoire et la réorganisation
documentaire sont postérieurs; voir l’[état courant](../status.md). Les permissions
et responsabilités ci-dessous s’appliquent au mandat daté, pas aux nouveaux lots.

## Mandat et frontières

L'utilisateur demande plusieurs tâches dans des processus séparés, avec revue
des plans, agents et subagents de développement, puis reviewers distincts.
Ce mandat couvre la planification et le développement local des lots ci-dessous.
Chaque tâche travaille dans son propre worktree et conserve ses résultats pour
intégration ultérieure. Le coordinateur possède ce document et la synthèse.

Le [plan du pilote](codex-mcp-email-pilot.md) reste la référence produit. Les
étapes 1–2 et leurs preuves sont conservées. Installation système, modification
de configuration Codex, connexion de comptes, téléchargement/exécution de
modèles, appels payants et envois réels restent hors de ces lots. Le mandat
initial ne demandait aucun commit. Le 20 septembre, l'utilisateur a autorisé
les branches et commits sources A/B/C, un commit de coordination séparé, puis
l'intégration locale et ses validations, d'abord laissée sans commit final.
La demande ultérieure de commit et de push autorise leur publication sur
`origin`; elle n'accepte pas le contrat produit B. Les fichiers d'instructions
publics et les expériences historiques restent inchangés.

## Lots indépendants

| Lot | Résultat demandé | Propriété des fichiers | Dépendance |
|---|---|---|---|
| A — Préparer l'isolation Linux | Adaptation du socket humain au service non privilégié; supervision et reprise; artefacts de déploiement et sondes | `pilots/codex_email/src/moraine_email/{human_server,server,policy}.py`, tests associés, `pilots/codex_email/deploy/`, `docs/pilot/linux-deployment.md`, `docs/plans/linux-isolation-preparation.md` | Socle actuel uniquement |
| B — Contrat d'ingestion | Plan technique prêt à décider, politique de publication proposée, provenance/versionnement et découpage d'implémentation | `docs/plans/email-ingestion-contract.md` et ses rapports de revue dédiés | Socle actuel et cadrage inspection; aucune dépendance au code A/C |
| C — Banc de qualification | Corpus fictif français/anglais annoté, validation du corpus, évaluation reproductible de prédictions fournies et rapport | Nouvelle arborescence `qualification/email_inspection/`, `docs/plans/email-inspection-qualification.md` | Cadrage inspection actuel; aucun contrat interne de B à présumer |

Chaque lot possède également ses preuves dans
`pilot-results/parallel-workstreams/<lot>/`. Les README propres aux nouveaux
répertoires appartiennent à leur lot. Les documents partagés existants, les
locks communs et le broker métier sont réservés au coordinateur : signaler un
besoin de modification plutôt que les changer depuis plusieurs tâches.

## Cycle de travail

1. Le responsable vérifie les instructions et la base effective du worktree,
   puis écrit un plan court avec fichiers, contrat, limites et critères mesurables.
2. Un reviewer distinct examine le plan, les dépendances et les preuves prévues.
   Le responsable corrige les constats bloquants; le reviewer confirme leur
   résolution avant développement.
3. Pour A/C, le responsable développe avec au moins un subagent sur un sous-lot
   indépendant et utile. Chaque délégation attribue les fichiers; tous savent
   qu'ils partagent le worktree et préservent les modifications des autres.
4. Deux reviewers distincts des auteurs examinent le résultat : conformité au
   plan/limites d'autorité, puis comportement/tests/oracles. Le responsable
   traite les constats; les reviewers revoient les corrections concernées.
5. Livraison : diff complet, commandes et résultats réellement exécutés,
   rapport de revue, limites et éléments restant à valider. Inclure les fichiers
   non suivis dans la revue; un diff de commits vide ne couvre pas le travail.

Le lot B s'arrête au plan revu : les propositions de politique restent des
propositions, une revue technique ne valant pas acceptation produit. Son auteur
peut déléguer une analyse indépendante et doit faire relire le contrat sous les
angles publication/autorité et implémentabilité/tests.

## Acceptation particulière

**A.** Conserver `SO_PEERCRED` et séparer droits de connexion au socket et UID
autorisé. Préparer des permissions sans `chown` vers un autre UID par le service
non privilégié. Arrêt/reprise doit considérer broker et OPA, ainsi que les
sockets obsolètes, sans effacer un endpoint actif. Les sondes multi-UID doivent
être exécutables par un administrateur dans une étape distincte. Rapporter
explicitement ce qui est testé localement et ce qui exige une installation;
aucune validation OS n'est déduite des seuls tests sous un UID.
Réexécuter la suite actuelle complète du pilote après les changements, ainsi
que les nouvelles vérifications locales d'arrêt/reprise et les sondes ciblées.
Observer indépendamment OPA après arrêt brutal du broker, défaillance d'OPA et
redémarrage; vérifier aussi qu'un endpoint actif est conservé. Distinguer le
comportement du code de celui qui dépendra du superviseur installé.

**B.** Couvrir corps, métadonnées et notes, entrées/sorties bornées, transformations
et versions, analyse partielle ou échouée, révocation pendant analyse, cache et
réinspection, séparation score/décision/autorisation. Recommander une seule
décision produit prioritaire et identifier ses conséquences. Prompt Guard est
retenu comme brique; variante, seuils et inspecteur génératif restent à qualifier.

**C.** Séparer corpus de réglage et d'évaluation. Identifier les cas ambigus et
leur annotation; couvrir messages longs et placements d'injection, entrées
malformées et citations légitimes. Les prédictions sont un artefact distinct du
corpus; détecter cas absents, dupliqués, versions incompatibles et couverture
incomplète. Un résultat non inspecté n'est jamais un verdict favorable. Tester
les métriques sur de petits exemples calculables; toute sortie synthétique
valide le banc seulement, jamais Prompt Guard. Aucun détecteur, poids ou modèle
réel n'est installé ou appelé. Éviter un framework générique de benchmarks.
Rapporter dénominateurs, cas non inspectés, cas ambigus et couverture séparément
pour réglage et évaluation; aucun score sur les seuls cas classifiés sans sa
couverture correspondante.

## Coordination et intégration

Les trois tâches démarrent indépendamment après revue de ce découpage. Le
coordinateur suit leurs jalons, transmet les décisions pertinentes et règle
les demandes de fichiers partagés. Les sources committées restent dans leurs worktrees;
leur intégration et leur validation combinée constituent le jalon autorisé suivant.
Gmail hors ligne sera un prochain lot, après consolidation des contrats utiles.

La tâche coordinatrice `01a0c091-9064-78d3-a2b9-2eb5bb1e8fbf` (hôte `local`)
est responsable de recueillir les résultats : `wait_threads` avec curseurs
pour suivre les jalons, puis lecture ciblée des rapports et artefacts. Les
responsables fournissent dans leur réponse finale le worktree, les rapports
et les validations manquantes. Une notification par `send_message_to_thread`
reste facultative et soumise à ses propres contrôles. Son refus ne transfère
pas à l'utilisateur la charge d'accéder aux tâches créées par le coordinateur;
le coordinateur consulte les résultats via ses outils de lecture autorisés.

Ce document était initialement non commité. Les mandats de création en donnent
le chemin absolu dans le checkout source, accessible en lecture seule depuis
les worktrees; ils reprennent les frontières et le cycle exigé. Chaque tâche
vérifie sa base effective avant de commencer. Aucun commit n'est nécessaire
pour transmettre les instructions de coordination.

| Lot | Tâche / worktree | État | Prochain jalon |
|---|---|---|---|
| A | `01a0c099-13e4-7001-81e1-9c0bc950f736` — `/home/alacasse/.codex/worktrees/cc8a/moraine` | Commit source conservé; intégré localement | Qualification système distincte |
| B | `01a0c099-2753-72f2-944c-95b2f24812e8` — `/home/alacasse/.codex/worktrees/49ae/moraine` | Proposition committée et intégrée, non acceptée | Décision produit avant implémentation |
| C | `01a0c099-3e47-7210-8668-ad7114dcd4f4` — `/home/alacasse/.codex/worktrees/d918/moraine` | Commit source conservé; intégré localement | Qualification d’un détecteur distincte |

Les mandats exacts et identifiants de création sont conservés dans
[`dispatch.json`](../../pilot-results/parallel-workstreams/dispatch.json).

### Livraison B

Le coordinateur a lu le contrat, le rapport et la validation, confirmé la fin
de tâche et vérifié les trois SHA-256 enregistrés. Quatre fichiers documentaires
nouveaux seulement; aucune production modifiée ou test applicatif exécuté.
Les constats résolus concernent les alertes persistantes entre sélections et
la borne des réessais. La recommandation sans dérogation de publication reste
proposée : aucune acceptation du contrat ou de ses autres hypothèses n'est
déduite de cette livraison. Les livraisons A/C ne dépendent pas de cette décision.

### Livraisons A et C

Le coordinateur a lu les rapports et les journaux finaux et vérifié les
13 empreintes du manifest A et les 11 du manifest C : aucune différence.
Les ensembles de fichiers modifiés/ajoutés des trois lots ne se chevauchent pas.
Les résultats ont ensuite été committés dans leurs worktrees respectifs, sans
modification des fichiers livrés. Leur import dans le checkout cible a été réalisé
sans commit final; les SHA ci-dessous remplacent les HEAD détachées initiales.

A livre permissions/socket, surveillance OPA, préparation du déploiement,
runbook et sondes. Deux reviewers non auteurs ont clôturé leurs constats;
la suite finale consigne 96 tests et 2 avertissements. La preuve distingue
OPA survivant au SIGKILL direct, son nettoyage par le harness et son absence
après arrêt gracieux du broker redémarré avant nettoyage. Installation
multi-UID, supervision systemd réelle et Codex dédié restent non exécutés.

C livre 24 cas fictifs, validation des prédictions fournies, métriques et
exemple artificiel. Deux reviewers non auteurs ont clôturé leurs constats;
13 tests et une sonde indépendante de 13 824 combinaisons sont consignés.
Le défaut de moyenne débordante a été corrigé et revu. Aucun modèle n'a été
qualifié; les résultats artificiels prouvent seulement le banc.

La notification C a été refusée par la revue automatique d'approbation, qui
jugeait insuffisamment établie l'autorisation de transmettre entre tâches.
Le coordinateur a consulté directement les livrables locaux et leurs preuves;
ce refus n'empêche donc plus de recueillir le résultat. Aucun nouveau besoin
d'autorisation n'est déduit pour cette consultation.

Après la précision de l'utilisateur sur son absence d'accès à C, le
coordinateur a confirmé la réception à cette tâche. C a répondu : livraison
récupérée et vérifiée, artefacts inchangés, aucune autorisation de notification
attendue. L'envoi refusé n'a pas été réessayé; aucune permission globale n'a été
modifiée. Cela clôt le suivi de C, sans corriger ni désactiver la revue automatique.

## Revue du découpage

`review_workstream_authority` et `review_workstream_delivery` ont chacun conclu
« prêt à lancer », en lecture seule, sans constat bloquant. Leurs compléments
sur la suite complète du pilote, l'observation d'OPA et les dénominateurs des
métriques sont intégrés aux critères ci-dessus. Cette revue porte sur le
découpage, pas sur les plans locaux ou les futures implémentations.

## Commits sources et intégration autorisée

Base commune de ces trois commits : `b63590cc02dbcb31859aeb683f4f71314beeb775`.
Chaque worktree source est propre; les preuves de livraison restent inchangées.

| Lot | Branche | Commit exact |
|---|---|---|
| A | `codex/linux-isolation-preparation` | `77b8b321dde3979941d23bb99653fd276d1070da` |
| B | `codex/proposed-ingestion-contract` | `559e26712a0cb7751e5785b4255e3dc0d3b57a0b` |
| C | `codex/email-inspection-qualification` | `cbfd364f392d93f640a78eb9c314b341d86aa428` |

Le [prompt d’intégration](../prompts/integrate-parallel-workstreams.md)
référence ces SHA. La coordination a été committée séparément avant import
(`342e2762400e612fa94f33fca25f0f16947e1aa0`).
L’import par `git cherry-pick --no-commit` a conservé les 46 fichiers et leurs
modes sans conflit. L’intégration a été validée avant son commit. La revue
du plan par `review_workstream_authority` est close sans
constat bloquant; le prompt exige `git diff HEAD` pour inclure l’index et les
fichiers non suivis sont inventoriés séparément.

Les commandes, résultats combinés, limites et revues actuelles sont conservés
dans le [rapport d’intégration](../../pilot-results/parallel-workstreams/integration-20260920/REPORT.md).
Les validations combinées réussissent et les deux contre-revues indépendantes
sont closes sans constat restant. Le rapport décrit l'état avant commit;
la [trace de préparation à la publication](../../pilot-results/parallel-workstreams/integration-20260920/publication.json)
consigne l'autorisation ultérieure et les seuls ajustements documentaires.
Les rapports A/B/C restent les preuves historiques de leurs livraisons, avec
leurs anciens états Git; aucune empreinte historique n’a été réécrite.

## Références

- [Étape 3 et étapes suivantes](codex-mcp-email-pilot.md#étape-3--séparation-linux-et-démonstration-depuis-codex-cli-23-jours)
- [Inspection du contenu](../research/email-content-inspection-sources.md)
- [Validation du socle](../../pilot-results/codex-email/20260920-steps-1-2/REPORT.md)
