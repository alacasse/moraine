# Lot A — préparation de l’isolation Linux

Base : `b63590cc02dbcb31859aeb683f4f71314beeb775`. Racine documentaire : `docs`.
Code et documentation appartiennent au dépôt Moraine. Plan local du 20 septembre 2026,
subordonné à `codex-mcp-email-pilot.md` §4/étape 3 et au découpage du coordinateur.

Statut : code et artefacts livrés, intégrés et testés localement; installation
multi-UID/systemd non qualifiée. Voir le [rapport d’intégration](../../pilot-results/parallel-workstreams/integration-20260920/REPORT.md)
et le [runbook actuel](../pilot/linux-deployment.md). Les responsabilités du lot
ci-dessous décrivent son mandat initial.

## Contrat et frontières

1. Le service conserve la propriété du socket. En mode séparé il utilise un groupe
   de connexion explicitement configuré et le mode 0660; il ne change jamais l’UID
   propriétaire. Le répertoire parent est administré pour être traversable par
   l’humain, non modifiable par lui. SO_PEERCRED reste le contrôle d’autorisation
   de l’UID humain, distinct des permissions permettant de connecter. Le défaut
   de démonstration sous un UID reste 0600.
2. Une exclusion locale stable protège la création/nettoyage du socket. Un endpoint
   actif est conservé, un fichier non socket ou de propriétaire inattendu est refusé;
   seul un socket obsolète appartenant au service, sous parent contrôlé, peut être
   récupéré. Le nettoyage ne retire que l’inode de cette instance.
3. OPA reste un enfant privé du broker. Son runtime est configurable dans un dossier
   privé du service. Une panne OPA ferme les décisions et provoque l’arrêt du broker
   pour permettre au superviseur de relancer l’ensemble. SIGKILL du broker ne peut
   exécuter le finally Python : systemd KillMode=control-group possède l’arrêt de
   tous les enfants avant reprise. Aucun mécanisme local n’est présenté comme une
   preuve de ce comportement systemd.
4. Des artefacts inspectables décrivent code/venv/politiques immuables sous /opt,
   configuration sans secrets sous /etc, secrets en fichiers privés du service,
   état 0700 sous /var/lib et runtime séparé sous /run. Une unité systemd modèle
   et des sondes opt-in accompagnent le runbook; aucune installation n’est faite.

## Répartition après revue du plan

- Subagent développement : `human_server.py`, nouveaux tests du socket uniquement.
  Interface prévue : `HumanServer(..., socket_gid: int | None = None)`.
- Responsable : `server.py`, `policy.py`, tests processus/runtime/déploiement,
  `deploy/`, `RUNBOOK.md`, ce plan et `pilot-results/parallel-workstreams/A/`.
- Aucun changement au broker métier, locks, docs partagés, AGENTS/CLAUDE ou preuves
  historiques. Pas de commit, publication, service installé, compte créé, modèle,
  compte email, API payante ou email réel. Les subagents partagent ce worktree.

## Validation et critères de livraison

- Plan relu par un agent distinct; blocages corrigés et confirmation avant code.
- Tests socket : mode/groupe réels du processus courant, aucun chown UID,
  refus SO_PEERCRED, endpoint actif préservé, récupération obsolète et refus
  chemins inappropriés. Les tests sous un UID ne prouvent pas l’isolation inter-UID.
- Tests processus réels avec OPA local : SIGKILL broker, observation indépendante
  du PID et du socket OPA avant nettoyage explicite; panne OPA, arrêt/reprise du
  broker; reprise d’un socket obsolète. Fournisseur simulé seulement. Aucun de ces
  cas n’est nommé crash en dispatch; la reprise métier déjà testée reste distincte.
- Suite complète actuelle du pilote, tests Rego puis Python et ciblés nouveaux.
  Réutiliser les dépendances locales, sans téléchargement. Conserver commandes,
  résultats, oracles et limites dans le rapport A.
- Sondes opt-in futures : identités réelles, groupes, accès effectifs fichiers,
  code/politiques non modifiables, socket inaccessible à l’agent, humain reconnu,
  membre du groupe non habilité refusé par SO_PEERCRED; contrôle du cgroup après
  arrêt brutal/reprise de l’unité installée. Les exécutions manquantes sont explicites.
- Deux contre-revues par agents non auteurs : conformité/autorité et comportement/
  tests/oracles, incluant nouveaux fichiers non suivis; corrections revues.

## Limites et intégration

La validation OS finale dépend de comptes distincts, de l’installation administrée
et du superviseur réel, des contrôles SELinux éventuels et de l’inventaire des ponts
Codex vers la session humaine. Le lot prépare ces vérifications sans les déclarer
réussies. L’intégration commune et la configuration Codex restent au coordinateur.

## Revue préalable

`/root/review_plan` (lecture seule, 20 septembre 2026) : plan prêt, aucun blocage.
Précisions retenues : appartenance effective du service au groupe socket; verrou
conservé toute la vie et identité `(st_dev, st_ino)`; récupération uniquement sur
`ECONNREFUSED` (jamais timeout/EACCES); sortie non nulle après panne OPA pour
`Restart=on-failure`; observation OPA avant tout nettoyage dans le test SIGKILL.
