# Provenance du pilote local

Point de départ Git : `5feab54` (sources, expériences A/B/C, revues et plan). L’extraction initiale a créé un pilote distinct sans importer ni modifier les modules des expériences. Les guides ont depuis été regroupés sous `docs/`; cette migration ne change pas le code expérimental.

- `experiments/b_broker/broker.py`, SHA-256 `83a5e2986ba4681ca78fee0d9679355022617966c66cd5d3bf4da5fc2c7ea292` : canonicalisation, SQLite WAL/FULL, verrou propriétaire et de cycle, intention avant IO, contrôles d'échéance après persistance, reprise conservatrice. Les inputs, tables, identité, projection, décisions, nonce et barrière d'incertitude sont adaptés au pilote.
- `experiments/b_broker/opa.py` et politiques : processus OPA réel, UDS/token privé, vérification stricte des résultats et absence de fallback. Politique email du pilote avec identités de configuration, pas Alice/Bob.
- `dependencies.lock.json` copié de B : OPA 1.9.0, Linux amd64, SHA-256 `66fa66f3b730b2fb086003863428b382b2898d343adb4b5dfab5598b4d739eed`. Le binaire local de l'expérience a été copié et vérifié sans modification de sa source; bootstrap du pilote permet l'acquisition reproductible.
- Nouveaux : MIME et validation restrictive, façade SDK MCP 1.30.0, socket humain, CLI, fournisseur indépendant sans déduplication et ses compteurs, validation en processus séparés.

Sources techniques vérifiées pendant le développement : [Codex MCP](https://learn.chatgpt.com/docs/extend/mcp?surface=cli), [SDK officiel](https://github.com/modelcontextprotocol/python-sdk), [distribution MCP](https://pypi.org/project/mcp/). Les API utilisées ont également été inspectées dans le SDK installé et figé par `uv.lock`.

Deux auteurs subagents distincts ont implémenté cycle/politiques et transports; le coordinateur a produit MIME/modèles/fournisseur et intégré le résultat. Des revues indépendantes ont détecté un budget HTTP incomplet, des bornes JSON insuffisantes, une échéance bearer non revérifiée après attente et un affichage ambigu des contrôles. Le test en vrais processus a également détecté un nettoyage SIGTERM incomplet; les corrections et leurs validations sont rapportées avec les preuves finales.

Ni la copie d'un module expérimental ni les tests ne prouvent l'isolation OS, l'intégration Codex réelle, OAuth ou Gmail. Ces étapes ne sont pas réalisées ici.

Les évolutions suivantes sont tracées séparément : [intégration A/B/C](../../pilot-results/parallel-workstreams/integration-20260920/REPORT.md),
puis [laboratoire local](../../pilot-results/local-lab/20260920/REPORT.md).
La [migration documentaire](../documentation.md) conserve les versions couvertes
par leurs manifests; ces empreintes historiques ne sont pas celles des guides actuels.
