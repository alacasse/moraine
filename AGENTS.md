# Travailler sur Moraine

Ce fichier contient les consignes publiques propres à ce dépôt. Code et
documentation maintenue ont le même propriétaire : le projet Moraine.
La racine documentaire est `docs/`; commencer par [son index](docs/README.md)
pour une question d'état, de plan ou d'architecture.

## Contexte à charger selon le travail

- État ou prochaine étape : [docs/status.md](docs/status.md). Distinguer ce qui
  est implémenté, validé localement, proposé ou encore à qualifier.
- Broker, MCP, socket humain, MIME ou persistance : lire
  [l'architecture](docs/architecture.md) et le [contrat](docs/pilot/interface.md).
- Démarrage, tests ou diagnostic du pilote : [guide](docs/pilot/README.md).
  Pour la console et les scénarios E2E : [laboratoire](docs/pilot/local-lab.md).
- Permissions Linux, unité systemd ou sondes : [runbook](docs/pilot/linux-deployment.md).
  Les sondes d'installation réelle sont distinctes des tests sous un seul UID.
- Ingestion : [contrat proposé](docs/plans/email-ingestion-contract.md).
  Sa revue technique ne vaut pas acceptation produit.
- Qualification d'inspection : [guide du banc](docs/qualification/email-inspection.md).
  Les prédictions artificielles ne sont pas des résultats de modèle.
- Expériences : [index historique](docs/experiments/README.md). Le pilote est une
  extraction indépendante; travailler dans le composant demandé.

## Invariants à préserver

- Les six outils MCP permettent demande d'accès, lecture, proposition et
  consultation du résultat. Demander un accès n'accorde aucun droit.
  Création/révocation des grants et décisions passent par le canal
  humain authentifié. Un contenu ou un champ fourni par l'agent n'accorde aucun droit.
- L'approbation porte sur un snapshot immuable, son digest et un nonce. Envoyer
  les octets MIME revus; conserver les contrôles de droits et d'échéance avant IO.
- `unknown` signifie résultat incertain : conserver la barrière persistante par
  compte/message source et l'absence de retry automatique. Observer l'effet
  chez le fournisseur indépendamment de la réponse du broker.
- Le laboratoire est un opérateur de test sous un UID, capable de simuler les
  deux rôles. Cela ne qualifie ni isolation OS, ni consentement humain réel,
  ni intégration de l'ingestion. Les textes de fixture restent des données.

## Développer et valider

Le code actif est sous `pilots/codex_email/`; ses dépendances et OPA sont verrouillés.
Depuis ce dossier, utiliser `./setup.sh` pour préparer un environnement manquant,
puis `./test.sh -q` pour la validation complète (OPA et pytest). Pour une correction
ciblée avec l'environnement prêt : `.venv/bin/python -m pytest tests/FICHIER.py -q`.
Les tests de processus nécessitent des sockets Unix et TCP loopback.

Le banc indépendant se teste depuis la racine avec
`python3 -m unittest discover -s qualification/email_inspection/tests -v`.
Choisir les validations selon les composants touchés; une modification purement
documentaire demande une vérification des chemins, liens et commandes, pas une
nouvelle campagne métier. Rapporter exactement les vérifications effectuées.

Le runtime du lab doit être neuf, privé et hors du dépôt. Préserver les jetons,
`connection.json`, bases et journaux privés hors Git. Conserver dans les preuves
uniquement les exports nécessaires et expurgés. Arrêter seulement les processus
créés par le travail en cours; préserver les exécutions et preuves antérieures.

## Documentation et livraison

Maintenir les guides dans `docs/` et les points d'entrée racine courts. Suivre
[docs/documentation.md](docs/documentation.md) pour déplacer un guide ou conserver
une preuve. Les plans/prompts historiques décrivent leur mandat daté; ils
n'autorisent pas de nouvelles opérations. Vérifier le mandat courant avant une
installation système, un compte distant, un appel payant ou un envoi réel.

Conserver les modifications préexistantes du workspace. Une autorisation de
commit/push d'un ancien lot ne vaut pas publication d'un nouveau lot. Pour un
commit auquel Codex contribue, ajouter exactement une fois :
`Co-authored-by: Codex <codex@openai.com>`.
