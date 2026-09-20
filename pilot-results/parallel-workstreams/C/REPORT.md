# Lot C — Corpus et banc hors modèle

Date : 2026-09-20. Base effective : `b63590cc02dbcb31859aeb683f4f71314beeb775`.
Worktree : `/home/alacasse/.codex/worktrees/d918/moraine`, HEAD détaché, propre
avant travail. Racine documentaire : `docs` (pas de configuration locale
`codex.docs-root` non vide); code et documentation dans le même dépôt.

## Livraison et portée

- [Plan et contrat local v1](../../../docs/plans/email-inspection-qualification.md).
- [Corpus, mode d'emploi et limites](../../../qualification/email_inspection/README.md).
- [Validateur et évaluateur](../../../qualification/email_inspection/evaluate.py).
- [Tests](../../../qualification/email_inspection/tests/test_evaluate.py).
- [Prédictions artificielles](../../../qualification/email_inspection/examples/artificial-predictions.json)
  et [rapport déterministe](../../../qualification/email_inspection/examples/artificial-report.json).

24 cas fictifs, 12 par split; chaque split comporte 6 FR/6 EN, 4 bénins,
6 injections, 1 ambigu, 1 malformé. Familles séparées avant mesure. Corps longs
15 803 et 16 190 caractères, attaque finale ou distribuée. Notes, métadonnées,
citations et obfuscations présentes. `attachment_text` est une surface fictive
supplémentaire, pas une extension des formats autorisés du pilote.

Python standard 3.14.7, sans dépendance ajoutée. Validation stricte des versions,
SHA-256 du corpus, IDs et doublons, types/classes/statuts et intervalles de
couverture. Rapport global, par split/langue/catégorie, dénominateurs et détail
par cas; absents et inspections partielles jamais transformés en prédiction
bénigne. Observations optionnelles déclarées séparées; aucune dans l'exemple.

L'exemple **artificiel** contient 19 cas déclarés inspectés, 2 partiels,
1 indisponible, 1 erreur, 1 absent. Parmi 20 cas évaluables, 16 sont classifiés :
TP=6, TN=6, FP=2, FN=2. Chaque split a TP=3, TN=3, FP=1, FN=1 sur 8/10 cas
évaluables. Ces nombres prouvent seulement le fonctionnement du banc sur des
valeurs inventées, jamais les performances de Prompt Guard ou d'un autre modèle.

## Provenance du cycle demandé

1. `/root` écrit le plan; `/root/review_plan` le relit en lecture seule et
   confirme explicitement « prêt au développement, aucun constat bloquant »
   avant création du code/corpus. Recommandations : surfaces vides, booléens et
   valeurs non finies, dénominateurs des non-classifiés, FP/FN/abstentions dans
   l'exemple. Elles sont couvertes par tests et exemple.
2. `/root` développe évaluateur, tests et exemple; `/root/corpus_author`
   développe simultanément corpus et README, avec propriété de fichiers
   distincte et consigne explicite de préserver les changements partagés.
3. `/root/review_plan`, non auteur, examine la conformité du résultat;
   `/root/review_metrics`, non auteur, examine comportement/tests/oracles.
   Les deux reçoivent explicitement les fichiers non suivis en revue.
   Conformité : prêt à livrer, aucun constat bloquant. Deux précisions mineures
   intégrées : `peak_rss_bytes` entier et surface `attachment_text` exploratoire,
   sans extension des pièces jointes du pilote. Reviewer conformité confirme
   les corrections et la fidélité de ce rapport.
4. Reviewer métriques : 12 tests initiaux réussis, 13 824 combinaisons
   indépendantes de vérités/classes/statuts examinées, rapport artificiel
   reproduit. Un P2 : trois observations `sys.float_info.max`, finies et valides,
   faisaient déborder la moyenne. Correction : `statistics.mean`, avec régression
   CLI sur les valeurs extrêmes et leurs effectifs. 13 tests passent après
   correction; reviewer confirme le P2 résolu, aucun constat bloquant restant.
   Il rejoue 13 824 combinaisons avec effectifs des non-classifiés, maximum
   fini et minimum subnormal positif. La sonde indépendante est conservée dans
   `review-matrix-probe.py` et son résultat dans `review-matrix-probe.log`.

## Commandes réellement exécutées

Depuis ce worktree :

```sh
python3 --version
python3 -m unittest discover -s qualification/email_inspection/tests -v
python3 pilot-results/parallel-workstreams/C/review-matrix-probe.py
python3 qualification/email_inspection/evaluate.py \
  --corpus qualification/email_inspection/corpus.json \
  --predictions qualification/email_inspection/examples/artificial-predictions.json \
  --output /tmp/moraine-C-artificial-report.json
cmp qualification/email_inspection/examples/artificial-report.json /tmp/moraine-C-artificial-report.json
git status --short
git diff --check
```

Résultats : Python 3.14.7; **13 tests réussis** (voir [journal](tests.log));
rapport régénéré identique byte à byte. Les tests lancent réellement la CLI
avec omissions, mode strict, données invalides et refus d'écraser une entrée;
ils vérifient que l'ancien rapport est conservé après entrée invalide. Matrice
asymétrique manuelle TP=3/FN=1/FP=2/TN=1 et inversion des prédictions, cas absents,
ambiguïtés, surfaces vides, division par zéro, fins de message et métadonnées
tronquées, provenance artificielle et observations finies sont exercés.
Première exécution pendant développement : 11 tests réussis et un échec de
fixture, car l'exemple n'était pas encore créé; aucune erreur masquée.

`git diff --check` ne couvre pas les fichiers non suivis; les reviewers lisent
ces fichiers directement. Le manifest de livraison recense leurs empreintes.
Une vérification Python des liens Markdown locaux et des espaces de fin de
ligne passe aussi; elle a permis de corriger les liens relatifs du présent
rapport avant livraison. Le [manifest](source-manifest.json) couvre les sources,
artefacts et preuves du lot (hors lui-même et caches Python).
Les fichiers suivis à la base restent inchangés. Aucun commit, push, fusion,
publication, téléchargement de poids ou exécution de modèle; aucune installation
système, configuration Codex, connexion de compte, API payante ou email réel.

## Limites et dépendances d'intégration

Le banc prouve validation locale des artefacts et arithmétique sur fixtures.
Il n'atteste pas que des intervalles déclarés ont été effectivement inspectés,
ni l'authenticité des observations ou de la provenance. Annotation éditoriale
sans consensus; familles proches requièrent revue humaine. Aucun modèle n'a
encore démontré détection, robustesse, limites de contexte, latence ou ressources.
Les fixtures de mesures dans les tests servent seulement d'oracles numériques.

Ni parsing MIME, ni fidélité des transformations, ni publication, révocation,
isolation ou droits du pilote ne sont validés. La suite du pilote n'est pas
relancée : aucun de ses fichiers ni dépendances n'est changé. L'intégration et
sa validation combinée restent au coordinateur. Le contrat v1 est local et
indépendant de B. Un futur runner devra qualifier versions/poids/runtime,
prétraitement, conversion des offsets et configuration, figer les choix sur
`tuning`, puis produire des prédictions `observed` traçables pour `evaluation`.
Aucun seuil ou résultat artificiel ne vaut décision produit ou sécurité.

## Transmission au coordinateur

Livraison locale complète. L'envoi du bilan par `send_message_to_thread` à la
tâche source explicitement nommée dans le mandat a été rejeté par le contrôle
automatique, puis rejeté de nouveau après vérification en lecture seule de
l'identité locale de la tâche. Motif : autorisation de divulguer chemins et
résultats entre tâches jugée insuffisamment établie. Aucun bilan n'a donc été
transmis par cet outil; cette notification attend une autorisation reconnue.
Cela ne bloque ni les artefacts locaux ni leur consultation par le coordinateur.
