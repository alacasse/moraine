# Lot A — préparation isolation Linux

État : **livré localement, deux contre-revues clôturées, 96 tests réussis** (20 septembre 2026).
Base exacte : `b63590cc02dbcb31859aeb683f4f71314beeb775`, worktree
`/home/alacasse/.codex/worktrees/cc8a/moraine`, documentation/code dans ce dépôt,
racine documentaire `docs`. Base conforme, worktree initial propre.

## Changements et provenance

- `/root` : plan A, `server.py` (arguments runtime/groupe, watchdog OPA), `policy.py`
  (runtime privé configurable), artefacts `deploy/`, runbook, tests processus et
  contrôles de préparation, rapport/preuves.
- `/root/socket_author` : `human_server.py` et `tests/test_socket_isolation.py`.
  Socket service 0600/0660, gid appartenant au service, UID pair conservé; verrou
  stable et reprise socket obsolète, préservation d’endpoint actif/inode remplacé.
- `/root/review_plan` : revue préalable en lecture seule, plan prêt sans blocage
  avant code. Précisions intégrées au plan (groupes, verrou/inode, ECONNREFUSED,
  code sortie panne OPA et observation de l’orphelin avant nettoyage).
- `/root/review_plan` : contre-revue finale conformité/autorité, fichiers non suivis
  inclus, clôturée après vérification des corrections; aucun constat restant.
- `/root/review_behavior` : contre-revue comportement/tests/oracles, nouveaux fichiers
  inclus, correction venv et précision de l’oracle d’arrêt; revue clôturée après
  relecture du déplacement de l’assertion avant le nettoyage du harness. Aucun
  constat restant. Les reviewers n’ont écrit aucun code.

Constats résolus : (1) mode socket OPA décrit via umask/parents0700, pas 0600;
(2) Python administré hors home explicitement choisi pour ProtectHome;
(3) gate compatible avec lib64->lib interne au venv, refus des liens de répertoire
externes et régression structurelle explicitement distincte des droits réels;
(4) preuve JSON renommée pour le refus HTTP sans token, nettoyage puis PID de
reprise consignés; absence d’OPA après arrêt gracieux observée **avant** le finally
killpg du harness pour ne pas lui attribuer le nettoyage du test.

## Commandes et observations réellement exécutées

Dépendances locales réutilisées : venv du checkout source, accessible via dossier
ignoré `.venv` (bin/lib liés au venv source et pyvenv.cfg copié); copie locale ignorée d’OPA, SHA-256
`66fa66f3b730b2fb086003863428b382b2898d343adb4b5dfab5598b4d739eed` vérifié.
`PYTHONPATH=src:.` assure l’import du worktree pendant les tests. Aucun téléchargement,
aucun lock modifié. Python 3.14.7; systemd-analyze 259.9.

Depuis `pilots/codex_email` :

- Subagent : `PYTHONPATH=src:. .venv/bin/python -m pytest tests/test_socket_isolation.py tests/test_human_review.py -q`
  → 33 passed, 5.20 s (21 nouveaux cas et 12 anciens).
- Responsable : `PYTHONPATH=src:. .venv/bin/python -m pytest tests/test_isolation_lifecycle.py -q --basetemp=/tmp/moraine-A-lifecycle-2`
  → 6 passed, 3.94 s.
- Suite complète : `PYTHONPATH=src:. ./test.sh -q --basetemp=/tmp/moraine-A-full-1`
  → **95 passed, 2 warnings, 23.32 s**; sortie dans `full-suite-1.log`.
  Les commandes OPA check/test du script terminent avec succès; aucune suite
  Rego dédiée n’est présente dans ce pilote (les politiques réelles sont exercées
  par Python). Les deux avertissements viennent de Starlette/AnyIO.
- Suite après correction du gate : même commande, `--basetemp=/tmp/moraine-A-full-2`
  → **96 passed, 2 warnings, 23.23 s**, `full-suite-2.log`.
- Suite après enrichissement JSON et avant déplacement de l’assertion :
  `--basetemp=/tmp/moraine-A-final`, sortie `full-suite-before-oracle-fix.log`.
  Cette version ne prouvait pas l’arrêt gracieux d’OPA indépendamment du harness.
- Suite finale après correction de cet oracle :
  `PYTHONPATH=src:. ./test.sh -q --basetemp=/tmp/moraine-A-final-reviewed`
  → **96 passed, 2 warnings, 23.19 s**, `full-suite-final.log`.
- Reviewer comportement : `PYTHONPATH=src:. /home/alacasse/projects/moraine/pilots/codex_email/.venv/bin/python -m pytest tests/test_deployment_preparation.py -q`
  → 5 passed (0.09 s); mêmes interpréteur/PYTHONPATH avec
  `tests/test_isolation_lifecycle.py tests/test_socket_isolation.py -q --basetemp=/tmp/moraine-A-review-behavior`
  → 27 passed (4.76 s), hors sandbox.
- `git diff --check` : réussi.
- Modèle rendu dans `/tmp/moraine-email.service` avec UID/GID d’exemple 1000;
  `systemd-analyze verify /tmp/moraine-email.service` hors sandbox → code 1,
  **seul diagnostic : exécutable /opt/moraine-pilot/.venv/bin/python absent**.
  Pas d’installation pour faire disparaître ce diagnostic; il doit être revérifié
  avec les vrais chemins et UID/GID lors de l’étape système.

Premières tentatives sous sandbox : sockets Unix/TCP refusés EPERM et OPA ne peut
écouter. Le contrôle positif du Python système a aussi été refusé sous les UID
apparents du sandbox, puis passé hors sandbox par le reviewer. Les tests sockets/processus ont été réexécutés hors sandbox avec autorisation
automatique, sans réseau distant. Deux commandes d’écriture lancées initialement
depuis le mauvais cwd n’ont créé aucun fichier; corrigées avant exécution. Ces
échecs d’environnement ne sont ni résultats produit ni contournements de tests.

L’oracle SIGKILL observe indépendamment `/proc` et une requête OPA non authentifiée
refusée : OPA reste vivant après la mort du broker sans superviseur. Ensuite seulement
le harness tue son groupe. Une nouvelle invocation récupère le socket humain obsolète.
La panne réelle d’OPA entraîne statut broker 1 et fermeture du socket; la relance
manuelle retrouve un nouveau processus OPA. Aucun dispatch en cours dans ces cas.

## Limites et dépendances d’intégration

Non faits : comptes/groupes/ACL/SELinux réels; installation /opt /etc /run /var/lib;
activation systemd, cgroup/restart automatiques; exécution des sondes inter-UID;
Codex sous UID dédié, inventaire de ses ponts/outils, compte Gmail, OAuth, modèle,
appel payant, email réel. Le fournisseur reste simulé. Aucun commit/push/fusion.
La préparation ne valide ni une isolation OS ni toute l’étape 3.

À l’installation future : gel code/venv non editable/politiques avec manifeste root,
identités et groupes réels, secrets service séparés, rendu/revue unité, vérification
statique sur cible puis sondes opt-in et parcours simulé inter-UID. L’unité supervise
broker+OPA; le serveur simulé et son oracle restent séparés. Les droits de connexion
au socket et l’habilitation UID sont contrôlés séparément. La récupération automatique
de stale socket suppose les parents administrativement contrôlés documentés.

Les sources métier, locks, documents partagés, instructions et expériences historiques
restent inchangés. Le coordinateur intégrera ce diff et les rapports avant la prochaine
étape système; README partagé pourrait ensuite pointer vers le nouveau RUNBOOK.


Les premières preuves JSON (fichiers préfixés `test_`) sont conservées telles
qu’exécutées; leur champ `opa_socket_authenticated` signifiait un **refus sans token**,
nom imprécis corrigé dans la preuve finale. La preuve finale distingue explicitement
observation avant nettoyage, nettoyage du groupe et arrêt gracieux après reprise.

Coordination : un premier envoi au coordinateur a été rejeté automatiquement pour
destination non vérifiée. Après lecture de la tâche source locale et vérification
du dépôt/titre/identifiant autorisé, le nouvel envoi a réussi; le coordinateur a
confirmé réception et demandé de conserver l’observation OPA et la traçabilité du
nettoyage. Aucun blocage d’autorisation restant.


## Livrables pour intégration

- `docs/plans/linux-isolation-preparation.md` : plan relu et contrat du lot.
- `pilots/codex_email/src/moraine_email/{human_server,server,policy}.py` : seules
  sources préexistantes modifiées; trois nouveaux fichiers de tests associés.
- `pilots/codex_email/deploy/` : unité modèle, configuration sans secrets,
  vérificateur d’installation et deux sondes opt-in.
- `pilots/codex_email/RUNBOOK.md` : installation future, droits, reprise et limites.
- `pilot-results/parallel-workstreams/A/` : rapport, journaux, preuves initiales et
  `final-process-evidence/` (seuls journaux et observations, aucun secret/état).
- `source-manifest.json` : SHA-256 des sources/livrables documentaires du lot,
  pour le transfert depuis ce worktree détaché; ne couvre pas les dépendances
  ignorées. HEAD est resté à la base exacte, aucun commit créé.
