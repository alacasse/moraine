# Lot C — Qualification locale de l'inspection email

Date : 2026-09-20. Base : `b63590cc02dbcb31859aeb683f4f71314beeb775`.
Statut : implémentation livrée et intégrée, contre-revues achevées. Le plan avait
été confirmé avant création du code et du corpus. Voir le
[rapport du lot C](../../pilot-results/parallel-workstreams/C/REPORT.md).
Autorité : [plan du pilote](codex-mcp-email-pilot.md), § 6, et mandat du lot C.
Code et documentation appartiennent au dépôt Moraine; racine documentaire `docs`.

## Périmètre et responsabilités

Créer seulement `qualification/email_inspection/`, ce document et
`pilot-results/parallel-workstreams/C/`. Aucun changement au pilote, aux locks,
aux expériences ou aux documents partagés. Python standard, sans dépendance
ajoutée, réseau, modèle, poids, détecteur ou compte réel. Le contrat ci-dessous
est propre au banc; il ne fige pas le contrat d'ingestion proposé par B.

Le responsable développe `evaluate.py` et `tests/test_evaluate.py`; un subagent
développe le corpus, ses annotations et son README. Ils partagent le worktree
et préservent leurs modifications respectives. Un reviewer distinct confirme
le plan avant code; deux reviewers non auteurs examinent ensuite tous les
fichiers, y compris non suivis : conformité/autorité puis comportement/oracles.

## Corpus et contrat v1

Un JSON UTF-8 `corpus.json` contient exactement `schema_version` (1),
`corpus_version` (chaîne non vide) et `cases` (liste non vide). Chaque cas porte
`id`, `version` (entier positif), `family`, `split` (`tuning` ou `evaluation`),
`language` (`fr` ou `en`), `categories` (liste de chaînes non vide), `label`
(`benign`, `injection`, `ambiguous` ou `malformed`), `rationale` (non vide),
et `input` (objet non vide dont chaque valeur est une chaîne).
Les clés de `input` nomment les surfaces à inspecter, par exemple `body`,
`subject`, `sender_name`, `note` ou `raw`. Les fixtures malformées sont donc du
texte brut encapsulé dans un corpus JSON valide; le banc ne parse pas du MIME.
Les catégories sont descriptives, multi-étiquettes; leurs comptes se chevauchent.

Prévoir environ 24 cas fictifs français/anglais : ordinaires, citations
légitimes, injections directes/indirectes/obfusquées, corps longs (au moins
12 000 caractères) avec attaque finale ou distribuée, métadonnées, notes,
entrées malformées et cas ambigus. Une famille (variantes ou traduction proche)
reste entièrement dans un split; rejeter familles partagées et entrées
identiques entre splits. Fixer les splits avant toute prédiction. Documenter
le jugement éditorial, ses ambiguïtés et l'absence de représentativité.

## Prédictions séparées et validation

Un fichier JSON contient exactement `schema_version` (1), `corpus_version`,
`corpus_sha256` (hash des bytes du corpus), `provenance` et `predictions`.
`provenance` contient `kind` (`artificial` ou `observed`), `producer` et
`description` non vides. Un artefact observé devra identifier dans ces champs
versions/poids/runtime/configuration et source des observations; le banc ne
certifie pas leur authenticité. Chaque ligne porte exactement `case_id`,
`case_version`, `status`, `label`, `score` et `coverage`, avec éventuellement
`observations`. Statuts : `inspected`, `partial`, `unavailable`, `error`.

`coverage` mappe chaque surface du cas à une liste d'intervalles `[start,end]`
en indices de caractères Python (demi-ouverts). Intervalles triés, disjoints,
bornés; aucune normalisation implicite. Une surface vide n'a aucun intervalle.
`inspected` exige couverture intégrale de toutes les surfaces, classe `benign`
ou `injection` et score numérique fini dans [0,1], orienté vers `injection`.
La classe est la décision déclarée du producteur; le banc n'impose pas de seuil.
Tous les autres statuts exigent classe et score `null`; `partial` exige une
couverture strictement partielle et non nulle; `unavailable`/`error` exigent
une couverture vide. Aucun résultat absent ou partiel ne devient favorable.

Rejeter types faibles (booléens pour nombres), champs inconnus, doublons JSON,
IDs inconnus/dupliqués, versions/hashes incompatibles, valeurs non finies,
classes/statuts incohérents et couverture invalide. Les cas absents sont
explicitement `missing` dans le rapport; option CLI `--require-complete`
écrit le rapport mais sort avec code 2 s'il en manque. Artefact invalide :
code 2, diagnostic, aucun nouveau rapport. Pas d'observations inventées :
`observations` optionnel ne contient que `latency_ms` et/ou `peak_rss_bytes`,
valeurs finies non négatives (`peak_rss_bytes` entier); interdit pour provenance
artificielle.

## Métriques et livrables

Rapport JSON déterministe sans horodatage ambiant : empreintes des deux
artefacts, provenance, version du banc, totaux globaux, par split, langue et
catégorie; détail par cas sans reproduire les textes. Pour chaque groupe :
cas totaux, étiquettes attendues, statuts (dont `missing`), cas inspectés,
caractères inspectés/attendus et leurs fractions, cas ambigus/malformés exclus,
cas évaluables (`benign`/`injection`), évaluables classifiés/non classifiés,
matrice TP/TN/FP/FN (positif = injection) et FPR/FNR/précision/rappel.
Chaque taux donne numérateur, dénominateur et valeur; dénominateur zéro donne
`null`. Les métriques binaires n'utilisent que les cas évaluables entièrement
inspectés, toujours accompagnées de la couverture. Afficher aussi les positifs
et négatifs attendus restés non classifiés. Les mesures optionnelles résument
seulement les observations fournies, avec leurs propres effectifs.

Livrer un exemple explicitement artificiel, incluant erreurs de classification
et non-inspection, et son rapport reproductible. Aucun seuil d'acceptation
modèle ni verdict de sécurité. Le banc démontre la validation du format et
l'arithmétique sur fixtures; aucun modèle n'a encore démontré sa détection,
sa résistance aux attaques, ses limites de contexte, sa latence ou ses ressources.
Les changements de sens, autorisations, révocations et publication ne sont
pas testés par ce banc de classification.

## Vérification et livraison

Tests `unittest` avec matrice asymétrique calculée à la main, inversion des
labels, omissions et abstentions, ambiguïtés, groupes vides/division par zéro,
types et versions invalides, doublons et couverture tronquée (notamment fin de
message/métadonnées), déterminisme et codes CLI. Validation du corpus livré et
reproduction exacte du rapport artificiel. Rapport compact des commandes,
résultats, provenance des reviewers, corrections et limites sous le lot C.
Pas de commit, push, fusion ou publication. L'intégration future et un runner
Prompt Guard exigent une qualification séparée des versions/poids/runtime.
