# Moraine

Moraine explore la délégation d'actions à un agent avec un contexte limité, des permissions explicites et une approbation humaine avant exécution.

Le pilote actuel prépare une réponse email en texte simple. L'agent consulte une sélection de messages via MCP et propose une réponse; l'humain relit le message figé dans un terminal séparé. Un broker OPA/SQLite contrôle les permissions, conserve la décision et effectue une tentative auprès d'un fournisseur simulé.

## État actuel

- Broker, quatre outils MCP, canal humain Unix et sérialisation MIME implémentés.
- Fournisseur simulé indépendant, sans déduplication, avec journal des tentatives et effets.
- 64 tests réussis dans la validation locale enregistrée, dont un parcours en processus séparés avec le SDK MCP officiel et OPA réel.
- Isolation entre utilisateurs Linux, intégration Codex réelle, OAuth/Gmail et livraison réelle encore à réaliser. Les essais actuels utilisent un seul utilisateur Linux et des données fictives.
- Couche d'inspection et d'assainissement du contenu entrant prévue, avec Prompt Guard comme l'une de ses briques de détection. Intégration, autres bibliothèques et éventuel inspecteur génératif restent à qualifier; aucune implémentation ni immunité aux injections n'est présumée.

## Démarrer

Le [guide du pilote](pilots/codex_email/README.md) décrit les prérequis, l'installation locale, les tests et la démonstration. Depuis `pilots/codex_email/`, sur Linux x86_64 avec Python 3.14 et `uv` :

```sh
./setup.sh
./test.sh -q
```

## Documentation et preuves

- [Plan du pilote](docs/plans/codex-mcp-email-pilot.md)
- [Pistes pour l'inspection et l'assainissement des emails](docs/research/email-content-inspection-sources.md)
- [Rapport de développement et validation](pilot-results/codex-email/20260920-steps-1-2/REPORT.md)
- [Provenance de l'implémentation](pilots/codex_email/PROVENANCE.md)
- [Expériences initiales A/B/C](experiments/README.md) et [comparaison](docs/experiments/COMPARISON.md)

Les expériences et leurs preuves sont conservées séparément du pilote. Les résultats locaux ne constituent pas une validation de l'isolation système ou d'un fournisseur email réel.
