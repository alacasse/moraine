# Mission : intégrer les trois lots Moraine

Travaille directement dans `/home/alacasse/projects/moraine`.

Intègre localement les livraisons A, B et C de leurs worktrees dans ce checkout,
harmonise la documentation utile, exécute les validations sur le résultat intégré
et fais revoir l'ensemble. Le livrable est un arbre de travail cohérent, testé
et prêt à examiner. Poursuis jusqu'à ce résultat, y compris les corrections
nécessaires dans ce périmètre; ne t'arrête pas à un plan ou à une copie de fichiers.

## 1. Périmètre et contexte

Lis les instructions applicables et résous la racine documentaire suivant
`codex.docs-root`, avec repli sur `docs`. Code et documentation appartiennent
au même dépôt Moraine. Lis ensuite :

1. `docs/plans/parallel-workstreams.md`, pour le découpage et la clôture des lots;
2. le plan `docs/plans/codex-mcp-email-pilot.md`, particulièrement étapes 3–4 et
   statut des décisions d'inspection;
3. les rapports de livraison A/B/C dans leurs worktrees, puis les fichiers ciblés.

**Autorisé par cette mission :** import local des fichiers livrés, résolution
des conflits d'intégration, corrections nécessaires, mises à jour documentaires,
tests locaux sur données fictives, subagents et reviewers indépendants.

**Hors périmètre pour cette phase d’intégration :** commit final d’intégration,
push, PR/publication, suppression des worktrees,
installation/activation de services ou création de comptes système, configuration
Codex, comptes Gmail/OAuth, email réel, téléchargement ou exécution de modèles,
API payante. Préserve les instructions `AGENTS.md`/`CLAUDE.md`, les expériences
historiques et leurs preuves. L'intégration n'adopte aucune décision produit
ouverte et ne démarre pas de nouvelle fonctionnalité.

## 2. Sources exactes et état de départ

Base commune vérifiée le 20 septembre 2026 :
`b63590cc02dbcb31859aeb683f4f71314beeb775`.

Les branches et commits sources ci-dessous ont été autorisés et créés avant
l’intégration. La coordination (`docs/plans/parallel-workstreams.md`, ce prompt
et `pilot-results/parallel-workstreams/dispatch.json`) est committée séparément
sur `master`. Vérifie son HEAD actuel et préserve toute évolution utilisateur.

| Lot | Branche | Commit exact |
|---|---|---|
| A | `codex/linux-isolation-preparation` | `77b8b321dde3979941d23bb99653fd276d1070da` |
| B | `codex/proposed-ingestion-contract` | `559e26712a0cb7751e5785b4255e3dc0d3b57a0b` |
| C | `codex/email-inspection-qualification` | `cbfd364f392d93f640a78eb9c314b341d86aa428` |

Les trois commits ont la base commune ci-dessus pour parent. Ils conservent
les preuves historiques décrivant les livraisons alors non committées.

| Lot | Worktree source | Livrables à intégrer et preuve |
|---|---|---|
| A — Préparation Linux | `/home/alacasse/.codex/worktrees/cc8a/moraine` | Les 13 fichiers de `pilot-results/parallel-workstreams/A/source-manifest.json`, puis tout le répertoire de preuves A. Seulement trois sources préexistantes modifiées : `pilots/codex_email/src/moraine_email/{human_server.py,server.py,policy.py}` |
| B — Contrat d'ingestion | `/home/alacasse/.codex/worktrees/49ae/moraine` | `docs/plans/email-ingestion-contract.md` et `pilot-results/parallel-workstreams/B/{work-plan.md,REPORT.md,validation.txt}`. Trois empreintes dans `validation.txt`; le journal lui-même n'y est pas hashé |
| C — Banc de qualification | `/home/alacasse/.codex/worktrees/d918/moraine` | `docs/plans/email-inspection-qualification.md`, `qualification/email_inspection/` hors caches, et tout `pilot-results/parallel-workstreams/C/`. Onze empreintes dans son `source-manifest.json` |

Rapport de chaque lot : `pilot-results/parallel-workstreams/<A|B|C>/REPORT.md`
dans son worktree. Les sources, plans, preuves et limites sont lisibles directement;
aucun accès utilisateur aux anciennes tâches n'est nécessaire. Le suivi de C
est clos : son ancien refus de notification n'est pas un blocage d'intégration.

## 3. Inventaire et revue du plan avant import

Vérifie les quatre HEAD et états Git, les parents des commits sources, les
manifests A/C et les empreintes B. Si l’intégration est déjà préparée, inventorie
et valide le travail existant sans réappliquer les commits ni effacer son index.
Les trois ensembles livrés ne se chevauchaient pas à la préparation de ce prompt.
Construis une liste explicite des fichiers de chaque commit à importer, avec
source, destination, empreinte et mode utile. Inclus toutes les preuves qui ne
sont pas couvertes par les manifests historiques et vérifie que les worktrees
sources ne comportent aucune livraison supplémentaire non committée.

Compare chaque destination existante à la base et à la livraison. Préserve toute
modification utilisateur. Une divergence est à analyser : résous les conflits
techniques dans ce mandat; sollicite l'utilisateur seulement lorsqu'une décision
produit ou la conservation de travaux contradictoires l'exige. Une empreinte
source différente doit être expliquée avant de réutiliser la revue historique.

Consigne un plan court d'intégration et fais-le examiner par un subagent en
lecture seule avant l'import. Corrige ses constats bloquants et obtiens leur
clôture. Il doit notamment vérifier exhaustivité de l'import, protection des
preuves, portée des décisions et validation du code réellement intégré.

## 4. Import et cohérence documentaire

Depuis une cible propre contenant le commit de coordination, applique :

```sh
git cherry-pick --no-commit 77b8b321dde3979941d23bb99653fd276d1070da 559e26712a0cb7751e5785b4255e3dc0d3b57a0b cbfd364f392d93f640a78eb9c314b341d86aa428
```

Vérifie que les fichiers et modes importés correspondent à l’inventaire.
Préserve les branches et worktrees sources. Aucun environnement `.venv`,
`.tools`, cache, fichier temporaire, base, socket ou secret ne doit être importé.
Garde intacts les rapports et manifests de livraison : ils décrivent leur
exécution historique. Toute correction d'intégration se documente dans un nouveau
rapport avec de nouvelles empreintes, sans réécrire leurs anciennes preuves.

Mets à jour les liens et statuts dans les documents partagés pertinents, notamment
`README.md`, le guide du pilote et `docs/plans/parallel-workstreams.md`; adapte
le plan principal ou `INTERFACE.md` seulement si le résultat intégré le nécessite.
Les mentions doivent distinguer :

- A : préparation de l'isolation et du déploiement réalisée; installation
  inter-UID, supervision systemd réelle et parcours Codex dédié non validés.
- B : contrat **proposé et revu, non accepté**. Sa recommandation de bloquer la
  publication sans dérogation reste à décider. Aucun cycle pré-grant, stockage
  d'inspection, outil humain supplémentaire ou politique de publication à coder ici.
- C : banc et corpus fictif utilisables. Aucun modèle exécuté ou qualifié;
  les chiffres de l'exemple artificiel ne mesurent pas Prompt Guard.

N'adapte pas le contrat du banc à l'API proposée de B : les lots ont été conçus
indépendamment. Aucune abstraction commune n'est nécessaire à leur intégration.

## 5. Validation sur le checkout intégré

Réutilise les dépendances locales vérifiées sans recopier un venv de worktree.
Vérifie l'interpréteur, OPA et la résolution des imports : ils doivent exercer
les sources de `/home/alacasse/projects/moraine`, pas celles d'un ancien worktree.
Si une dépendance manque, identifie précisément ce manque et termine les
vérifications indépendantes. Respecte les mécanismes d'approbation des outils
pour les sockets/processus; ne transforme pas un refus de sandbox en échec produit.

Exécute et conserve les commandes, sorties et codes de retour :

- Depuis `pilots/codex_email/` : `PYTHONPATH=src:. ./test.sh -q`, avec un
  `--basetemp` neuf sous `/tmp` si nécessaire. La livraison A enregistrait
  **96 tests réussis, deux avertissements**, avec OPA réel et fournisseur simulé.
- Depuis la racine :
  `python3 -m unittest discover -s qualification/email_inspection/tests -v`.
  La livraison C enregistrait **13 tests réussis**.
- `python3 pilot-results/parallel-workstreams/C/review-matrix-probe.py` :
  la sonde indépendante enregistrait **13 824 combinaisons** et les valeurs
  numériques extrêmes. Puis régénère l'exemple artificiel avec la CLI documentée
  du banc vers un fichier temporaire et compare-le au rapport livré.
- Vérifie les liens locaux, les espaces de fin de ligne et `git diff --check`.
  Ce dernier ne couvre pas les fichiers non suivis : contrôle-les explicitement.
- Vérifie la correspondance des fichiers importés aux sources, puis inventorie
  séparément les éventuelles corrections d'intégration. Confirme que les
  expériences historiques, leurs preuves et les locks de dépendances sont intacts.

Garde les observations de processus précises : OPA survit au SIGKILL direct du
broker sans superviseur; le harness le nettoie ensuite. L'arrêt gracieux d'OPA
après reprise doit être observé avant le nettoyage du harness. Aucun crash
pendant un envoi ni comportement systemd réel n'est démontré par ces tests.
Les sondes inter-UID/cgroup opt-in restent réservées à l'installation future.

Les compteurs historiques servent de comparaison, pas de résultats à recopier.
Explique tout écart. Ne répète les suites qu'après correction ou problème nouveau.

## 6. Contre-revue et livraison

Fais examiner le résultat intégré par deux subagents distincts de son auteur,
en lecture seule et sur **tout** le diff, nouveaux fichiers compris.
`cherry-pick --no-commit` remplit l’index : utiliser `git diff HEAD`
(ou staged + unstaged), puis examiner les fichiers non suivis séparément :

1. conformité aux lots, décisions encore proposées, cohérence des contrats et docs;
2. comportement, tests/oracles, provenance et limites des nouvelles preuves.

Traite leurs constats pertinents et fais revoir les corrections. Si tu délègues
une correction, attribue explicitement ses fichiers et rappelle que les agents
partagent le checkout : ils préservent les modifications des autres. Récupère
toi-même leurs résultats; ne demande pas à l'utilisateur de contacter une tâche
que tu as créée. Aucune nouvelle tâche de l'application n'est nécessaire.

Crée les preuves d'intégration dans un nouveau répertoire sous
`pilot-results/parallel-workstreams/`, distinct de A/B/C, avec : rapport,
inventaire des transferts, commandes/résultats actuels, auteurs/reviewers et
constats résolus, manifest final des fichiers intégrés ou corrigés. Mets à jour
le suivi central en liant cette preuve.

**Critère de fin :** A/B/C présents dans le checkout cible, aucun fichier de lot
omis sans justification, documentation cohérente, validations exécutables
réussies, revues closes sans constat bloquant et limites restantes explicites.
Termine avec les chemins utiles, le résumé du diff et les vrais résultats de
validation. Laisse l’intégration non committée et les worktrees sources disponibles.
Les commits sources et celui de coordination restent conservés.
Si une validation reste matériellement bloquée, distingue clairement
« intégration préparée » de « intégration validée » et décris le blocage exact.
