# Moraine

Moraine explore une brique open source qui contrôle les accès et les actions
qu'un humain délègue à un agent. Le modèle consulte un contexte limité et propose
une action; un service indépendant vérifie ses droits, conserve le message exact
et attend l'approbation avant d'effectuer une tentative d'envoi.

Le pilote actuel prépare une réponse email en texte simple à un seul destinataire.
Il utilise un vrai broker Python, OPA, SQLite, quatre outils MCP et un canal humain
Unix. Le fournisseur email est simulé et observe ses tentatives et effets dans
ses propres journaux.

## Essayer en local

Le laboratoire web permet à l'utilisateur ou à l'assistant de lire le contexte,
rédiger, proposer, simuler une décision humaine et vérifier la boîte reçue. Il
lance aussi neuf scénarios E2E reproductibles. Aucun compte fournisseur n'est
nécessaire; l'assistant utilise sa session existante, sans modèle embarqué dans
le laboratoire.

Prérequis : Linux x86_64, Python 3.14 et `uv`. Depuis la racine du dépôt :

```sh
cd pilots/codex_email
./setup.sh
./test.sh -q
PYTHONPATH=src:. .venv/bin/python -m lab serve \
  --state-dir /tmp/moraine-lab-demo --port 8790
```

Le setup télécharge les dépendances publiques verrouillées et OPA si nécessaire;
il n'installe rien globalement. Ouvrir `http://127.0.0.1:8790`, puis utiliser le
jeton du fichier privé `/tmp/moraine-lab-demo/connection.json`. Choisir un nouveau
dossier à chaque lancement. Le [guide du laboratoire](docs/pilot/local-lab.md)
détaille la connexion, les scénarios, les preuves et le nettoyage.

## État et limites

Le parcours navigateur assisté et la campagne automatique ont été validés avec
des données fictives. Les [résultats datés et travaux restants](docs/status.md)
distinguent code livré, préparation Linux, propositions et garanties non testées.

Les processus du laboratoire partagent un utilisateur Linux, et l'opérateur de
test joue les deux rôles. Cette validation ne prouve pas l'isolation système ni
une livraison email réelle. La couche d'inspection et le rôle de Prompt Guard
sont retenus; le contrat d'ingestion reste proposé et cette couche n'est pas
implémentée. Aucun modèle Prompt Guard n'est installé ou qualifié.

## Se repérer

| Besoin | Point d'entrée |
| --- | --- |
| Documentation, plans et recherches | [Index documentaire](docs/README.md) |
| Composants, données et frontières d'autorité | [Architecture actuelle](docs/architecture.md) |
| Développement, tests et interfaces du pilote | [Guide du pilote](docs/pilot/README.md) |
| Installation Linux séparée à qualifier | [Runbook](docs/pilot/linux-deployment.md) |
| Évaluer des prédictions d'inspection fournies | [Banc de qualification](docs/qualification/email-inspection.md) |
| Comparer les trois prototypes historiques | [Expériences](docs/experiments/README.md) |
| Consignes pour les agents de développement | [AGENTS.md](AGENTS.md) |

La documentation maintenue se trouve sous `docs/`. `pilots/` contient le pilote,
`qualification/` le banc hors modèle et `experiments/` les prototypes. Les preuves
datées restent avec leurs artefacts dans `pilot-results/` et les répertoires
historiques des expériences; voir la [politique documentaire](docs/documentation.md).
