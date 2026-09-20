# Intégration locale des lots A/B/C

Date : 20 septembre 2026. Auteur de l'intégration : coordinateur `/root`, tâche
`01a0c091-9064-78d3-a2b9-2eb5bb1e8fbf`. Cible :
`/home/alacasse/projects/moraine`, branche `master`.
Statut : **intégration locale validée, deux contre-revues closes sans constat
restant**. Résultat prêt à examiner et à committer, laissé non committé.

## Commits conservés et autorisation

L'utilisateur a demandé de réaliser les branches et commits sources, le commit
séparé de coordination, puis l'intégration et les validations locales. Le résultat
intégré reste volontairement **non committé**; aucun push ni publication.

| Lot | Branche | SHA |
|---|---|---|
| A | `codex/linux-isolation-preparation` | `77b8b321dde3979941d23bb99653fd276d1070da` |
| B | `codex/proposed-ingestion-contract` | `559e26712a0cb7751e5785b4255e3dc0d3b57a0b` |
| C | `codex/email-inspection-qualification` | `cbfd364f392d93f640a78eb9c314b341d86aa428` |
| Coordination | `master` avant import | `342e2762400e612fa94f33fca25f0f16947e1aa0` |

Les quatre commits ont pour parent commun
`b63590cc02dbcb31859aeb683f4f71314beeb775` et portent chacun une seule attribution
`Co-authored-by: Codex <codex@openai.com>`. Les worktrees sources sont propres et
leurs branches restent disponibles. Aucun fichier livré n'a été changé avant commit.

## Plan revu et import

Le reviewer `review_workstream_authority`, distinct des auteurs des lots et de
l'intégration, a conclu « prêt à exécuter », sans blocage. Ses précisions ont été
intégrées au prompt avant import : portée temporelle des commits et revue par
`git diff HEAD` pour inclure les fichiers placés dans l'index.

Le [prompt](../../../docs/prompts/integrate-parallel-workstreams.md) conserve les
SHA exacts et évite une double application si le résultat est déjà présent.
La cible était propre après le commit de coordination. Import par
`git cherry-pick --no-commit` des trois SHA, dans l'ordre A/B/C : code 0, aucun
conflit. L'[inventaire](import-inventory.json) compte **46 fichiers** disjoints
(A : 30; B : 4; C : 12), avec chemins source/cible, objets Git, modes et SHA-256.
Tous correspondaient aux commits immédiatement après import. Les 13 empreintes
historiques A, trois B et 11 C concordaient avant commit et restent conservées.

Les seules adaptations d'intégration portent sur les documents partagés :
`README.md`, `pilots/codex_email/README.md`, `pilots/codex_email/INTERFACE.md`,
`docs/plans/codex-mcp-email-pilot.md` et `docs/plans/parallel-workstreams.md`.
Elles raccordent les livrables, documentent les options de lancement existantes
et distinguent préparation locale, décision produit et qualification système.
Aucun code source, test, dépendance ou preuve A/B/C n'a été corrigé à l'intégration.

## Validations actuelles

Les [commandes, environnements, dates et codes](commands.json) désignent cette
exécution, pas les compteurs historiques. Toutes ont retourné 0.

| Vérification | Résultat actuel | Preuve |
|---|---|---|
| Python et imports du pilote; version/hash OPA | Sources du checkout cible; Python 3.14.7; OPA 1.9.0 et checksum attendu | [provenance](runtime-provenance.log) |
| `PYTHONPATH=src:. ./test.sh -q --basetemp=…` depuis le pilote | 96 tests réussis, 2 avertissements, 23,44 s; commandes OPA check/test réussies, sans suite Rego dédiée; politiques exercées par les tests Python | [suite](pilot-suite.log) |
| `python3 -m unittest discover -s qualification/email_inspection/tests -v` | 13 tests réussis | [tests](qualification-tests.log) |
| Sonde C indépendante réexécutée | 13 824 combinaisons, extrêmes finis et sous-normaux réussis | [sonde](matrix-probe.log) |
| CLI sur prédictions artificielles, puis `cmp` | Rapport identique au rapport livré | [CLI](artificial-evaluation.log), [comparaison](artificial-report-comparison.log) |

Les deux avertissements sont les dépréciations Starlette/httpx et
AnyIO BlockingPortal déjà observées dans A. Les locks n'ont pas été changés.
Les secrets fictifs et l'état temporaire restent hors dépôt; seules les
observations expurgées de processus sont conservées dans `process-evidence/`.
L'observation d'OPA après arrêt gracieux du broker redémarré précède le nettoyage
du harness, conformément à l'assertion du test intégré.

## Contre-revues et intégrité

Les deux reviewers sont distincts des auteurs A/B/C et de l'auteur d'intégration.
Ils examinent `git diff HEAD`, les nouveaux fichiers et ces preuves.

- `review_workstream_authority` : contre-revue conformité/décisions/docs close,
  aucun constat restant après relecture. Son P3 sur les commandes OPA a été
  corrigé : aucune suite Rego dédiée n'est revendiquée. Aucun test réexécuté.
- `review_workstream_delivery` : contre-revue comportement/tests/oracles/provenance
  close, aucun constat actionnable restant après relecture de la précision OPA.
  Vérification indépendante des 46 imports et réexécution ciblée de `opa test`
  (code 0, aucun cas et aucune sortie); aucune répétition de la suite complète.

Le [contrôle d'intégrité](integrity-checks.log) vérifie les 46 fichiers importés,
les commits et les 239 fichiers préexistants hors changements autorisés :
bytes et modes identiques à la base, expériences et locks compris. Les chemins
des liens Markdown locaux existent; leurs fragments d'ancrage ne sont pas
contrôlés automatiquement. `git diff HEAD --check` et le contrôle de l'index
réussissent. Les sources, documents, JSON et nouveaux fichiers ont été inspectés
pour les espaces terminaux. Un espace dans la sortie OPA `Build Hostname: `
reste conservé tel quel dans le journal de provenance.

Le manifest final `source-manifest.json` enregistre les SHA-256 et modes des
fichiers importés, des documents de coordination/intégration et des nouvelles
preuves. Il exclut seulement son propre contenu pour éviter une empreinte
circulaire; il est généré après clôture du rapport et du journal d'intégrité.

## Limites maintenues

- A prépare l'installation; aucune création de comptes, installation systemd,
  sonde inter-UID/cgroup ni session Codex dédiée n'a été exécutée. Le diagnostic
  historique `systemd-analyze verify` sur un Python `/opt` absent n'est pas une
  validation complète d'installation. OPA survit au SIGKILL direct du broker
  sans superviseur; le harness le tue ensuite. Aucun crash pendant dispatch
  n'est revendiqué par ces nouvelles observations.
- B reste un **contrat proposé et revu, non accepté**. Le blocage de publication
  sans dérogation et les nouvelles surfaces de sélection/stockage ne sont pas
  implémentés. L'intégration n'adopte aucune hypothèse produit supplémentaire.
- C valide un banc et un corpus éditorial fictif. Les prédictions d'exemple
  sont artificielles; aucun modèle, Prompt Guard compris, n'est évalué ou
  qualifié. Couverture déclarée et scores ne constituent pas une attestation.
- Aucun compte email, Gmail/OAuth, appel modèle/API payante ou envoi réel.

Les preuves de livraison A/B/C restent historiques et intactes, y compris leurs
mentions d'anciens HEAD et de fichiers alors non suivis. Les nouvelles preuves
ne les remplacent pas. Expériences, preuves antérieures et locks sont conservés.
