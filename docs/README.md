# Documentation de Moraine

Cette arborescence rassemble la documentation maintenue du projet. Le
[README racine](../README.md) présente Moraine et permet de démarrer; les
[consignes agents](../AGENTS.md) orientent le développement.

## Comprendre et utiliser l'existant

| Sujet | Document | Portée |
| --- | --- | --- |
| Situation du projet | [État et suites possibles](status.md) | Livré, validé, proposé, restant |
| Composants et autorité | [Architecture](architecture.md) | Implémentation actuelle |
| Préparer et tester | [Pilote email MCP](pilot/README.md) | Simulation, dépendances, commandes |
| Manipuler le parcours et diagnostiquer | [Laboratoire local](pilot/local-lab.md) | Navigateur, scénarios, preuves |
| Développer les interfaces | [Contrat du pilote](pilot/interface.md) | Broker, MCP, canal humain, fournisseur |
| Demander un accès depuis Codex | [Parcours agent](pilot/agent-access.md) | Demande persistante, décision locale, lecture simulée |
| Comprendre l'extraction | [Provenance](pilot/provenance.md) | Origine expérimentale et adaptations |
| Préparer des identités Linux séparées | [Déploiement Linux](pilot/linux-deployment.md) | Installation et sondes restant à qualifier |
| Évaluer des prédictions fournies | [Qualification d'inspection](qualification/email-inspection.md) | Corpus fictif et métriques, hors modèle |
| Retrouver les chemins et preuves | [Organisation documentaire](documentation.md) | Maintenance, migration, archives |

## Plans et décisions

- [Plan du pilote](plans/codex-mcp-email-pilot.md) : direction broker/MCP,
  étapes initiales et hypothèses de déploiement ultérieur.
- [Laboratoire local](plans/local-e2e-lab.md) : périmètre et acceptation réalisés.
- [Demande d'accès depuis Codex](plans/agent-access-pilot.md) : lot autorisé,
  demande persistante, décision humaine locale et lecture par API d'emails fictifs.
- [Préparation Linux — lot A](plans/linux-isolation-preparation.md) : code et
  artefacts livrés; installation multi-UID/systemd non qualifiée.
- [Ingestion — lot B](plans/email-ingestion-contract.md) : proposition revue,
  sans acceptation produit ni implémentation.
- [Qualification — lot C](plans/email-inspection-qualification.md) : contrat
  du banc et du corpus implémentés, aucun détecteur qualifié.
- [Coordination des lots](plans/parallel-workstreams.md) : historique des tâches,
  commits sources, intégration et publication A/B/C.

Les [prompts de planification](prompts/plan-codex-mcp-email.md) et
[d'intégration](prompts/integrate-parallel-workstreams.md) sont des mandats
historiques exécutés. Lire leur statut avant de les réutiliser.

Pour poursuivre la discussion : [prompt de reprise côté agents](prompts/explore-agent-moraine.md).
Il relie leur connexion, leurs demandes et leur reprise après approbation aux
questions produit ouvertes; son mandat est une exploration.

## Expériences et recherches

L'[index des expériences](experiments/README.md) relie les contrats, guides A/B/C,
plans, implémentations, revues et comparaison historiques. Les lettres A/B/C de
ces prototypes désignent d'autres objets que les lots récents ci-dessus.

Les recherches sont datées et ne valent pas qualification du projet :

- [Autorité déléguée et positionnement](research/delegated-authority-investigation.md)
- [Délégation, autorisation humaine et gestion des accès](research/delegation-ux-multi-provider.md) :
  exploration du 21 septembre 2026, plusieurs fournisseurs, mobile/web, accès
  continu et suspension pour inactivité; huit questions à reprendre et choix
  produit ouverts.
- [Standards de délégation](research/delegation-standards-sources.md)
- [Moteurs de politique et recouvrements](research/policy-overlap-sources.md)
- [Identités, MCP et approbation](research/identity-mcp-approval-sources.md)
- [Inspection et assainissement des emails](research/email-content-inspection-sources.md)
- [Étude de LLM Guard](research/llm-guard-qualification.md)

## Preuves

Les rapports et artefacts datés restent sous `pilot-results/` et dans les dossiers
historiques des expériences. L'[état du projet](status.md) pointe vers les preuves
pertinentes. Leurs commandes, chemins, nombres de tests et empreintes décrivent
l'arbre testé à cette date, pas automatiquement le checkout courant.
