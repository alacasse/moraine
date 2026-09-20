# Pilote email MCP — étapes 1 et 2

Implémentation locale sur **fournisseur simulé**, issue de [B](../../experiments/b_broker/README.md) et du [plan revu](../../docs/plans/codex-mcp-email-pilot.md). Elle permet de déléguer quelques textes, proposer une réponse via le SDK MCP officiel, approuver/refuser par un socket humain, puis consulter le résultat durable.

Les exemples utilisent le même utilisateur Linux. Ils prouvent les contrôles applicatifs et le protocole, **pas l'isolation OS**. Aucun compte fournisseur, OAuth, envoi réel ou configuration Codex n'est installé. La séparation des utilisateurs et l'essai depuis Codex appartiennent à l'étape 3; Gmail aux étapes 4–5.

## Préparer et tester

Linux x86_64, Python 3.14 et `uv` sont nécessaires. Depuis ce dossier :

```sh
./setup.sh
./test.sh -q
```

Le setup acquiert OPA 1.9.0 vérifié SHA-256 et les dépendances verrouillées dans ce seul dossier. Il ne télécharge pas Python et n'utilise aucun compte. Les tests nécessitent des sockets Unix et TCP loopback. L'environnement `.venv`, le cache et le binaire sont ignorés par Git; les locks et sources sont versionnables. Le SDK utilisé est `mcp==1.30.0`, branche 1.x maintenue; aucune dépendance implicite à l'API 2.x.

`tests/test_process_workflow.py` lance réellement fournisseur, broker/OPA et client MCP officiel dans des processus distincts. Il ferme la session, redémarre le broker, approuve par socket humain, vérifie les bytes MIME chez le fournisseur, puis répète la demande et révoque. Les autres suites testent notamment erreurs OPA, nonce/digest, concurrence, replay, délais SQLite/IO, panne du commit après effet, barrière `unknown` et refus de nouvelles divulgations.

## Démonstration manuelle, données fictives seulement

Créer un dossier nouveau (il ne doit pas déjà exister) :

```sh
.venv/bin/python examples/prepare_demo.py /tmp/moraine-email-demo
```

Dans un premier terminal, depuis ce dossier :

```sh
.venv/bin/python -m tests.fixtures.provider_server \
  --directory /tmp/moraine-email-demo/provider \
  --token-file /tmp/moraine-email-demo/provider-token --port 8099
```

Dans un deuxième terminal :

```sh
.venv/bin/moraine-email \
  --state-dir /tmp/moraine-email-demo/state \
  --config /tmp/moraine-email-demo/config.json \
  --agent-token-file /tmp/moraine-email-demo/agent-token \
  --provider-token-file /tmp/moraine-email-demo/provider-token \
  --provider-url http://127.0.0.1:8099 --opa-binary .tools/opa \
  --human-socket /tmp/moraine-email-demo/human.sock \
  --human-uid "$(id -u)" --port 8765
```

Dans le terminal humain, créer la délégation avant l'expiration du fichier d'exemple :

```sh
.venv/bin/moraine-human --socket /tmp/moraine-email-demo/human.sock \
  create-grant /tmp/moraine-email-demo/grant.json
```

Copier le `grant_id` retourné, puis exécuter le client agent avec son seul jeton :

```sh
.venv/bin/python examples/agent_client.py \
  --token-file /tmp/moraine-email-demo/agent-token propose GRANT_ID
```

La réponse est `pending`; le processus client peut s'arrêter. Dans le terminal humain, copier le `request_id` :

```sh
.venv/bin/moraine-human --socket /tmp/moraine-email-demo/human.sock review REQUEST_ID
```

Lire tout le message et saisir `approve` ou `reject`. Le corps est présenté ligne par ligne; contrôles et antislashs sont échappés de manière distincte. La décision porte sur le digest et le nonce de cette vue. Toute modification impose une nouvelle demande et une nouvelle revue. L'approbation doit arriver dans les cinq minutes et avant l'expiration du grant.

```sh
.venv/bin/python examples/agent_client.py \
  --token-file /tmp/moraine-email-demo/agent-token status REQUEST_ID
.venv/bin/moraine-human --socket /tmp/moraine-email-demo/human.sock revoke-grant GRANT_ID
```

`accepted` signifie que le simulateur a enregistré l'effet; la livraison reste `unverified`. Vérifier `provider/attempts.jsonl` et `provider/effects.jsonl` pour comparer les octets réellement soumis. `rejected` n'ajoute aucun effet. Après révocation, un résultat terminal reste vrai mais ses contenus sensibles ne sont plus exposés à l'agent. Arrêter les services avec Ctrl-C; ne pas réutiliser ces jetons de démonstration pour un autre contexte.

## Contrôles et limites

- Quatre outils MCP seulement : `list_context`, `read_context`, `propose_reply`, `get_request`. Aucun appel MCP ne peut créer, approuver ou révoquer une délégation. Les autres outils d'un futur client Codex ne sont pas confinés par cette interface.
- Les identités configurées restent stables : un humain, un agent, une boîte. `SO_PEERCRED` authentifie le pair Unix. Les inputs ne peuvent fournir une identité d'approbateur. Le bearer MCP est considéré lisible par l'agent; seule son empreinte est conservée par la façade, et sa session expire après 24 heures. Révocation immédiate du bearer : arrêter le service; remplacer le fichier par un nouveau token avant redémarrage. Ce n'est pas un système de gestion de sessions multicomptes.
- Les secrets sont fournis dans des fichiers privés, distincts et appartenant au compte de lancement, jamais dans les arguments. L'installation fiable des fichiers, utilisateurs/groupes, politiques et sockets est encore à valider à l'étape 3. Le home partagé de cette démo donne à son propriétaire tous les pouvoirs.
- Sélection immuable : 1–5 messages texte et au plus une note; 32 Kio par texte, 128 Kio total. Réponse texte UTF-8 de 16 Kio maximum, un destinataire, aucun Cc/Bcc, HTML ou fichier joint. Les adresses acceptées forment un sous-ensemble ASCII strict, sans noms affichés, groupes ou parties locales entre guillemets.
- Le MIME est produit une seule fois, contrôlé par aller-retour, persisté puis envoyé sans reconstruction. L'approbation/refus et le traitement d'incertitude sont audités. OPA réel vérifie la politique; aucune permission de secours n'existe en cas de panne.
- Un unique broker détient la base. Les opérations sont sérialisées; une révocation peut attendre derrière un appel déjà parti. L'adaptateur a un budget total de quatre secondes, y compris en-têtes et corps, sans retry. Les garanties d'échéance concernent le dernier contrôle local, pas l'heure d'acceptation distante.
- Un résultat `unknown` ou une intention non résolue bloque toutes les autres demandes pour le même compte/message, même sous un nouveau grant. Le redémarrage ne renvoie rien. `resolve-unknown` exige un acte humain explicite avertissant du risque de doublon et ne transforme pas le résultat passé en échec certain. Si le stockage échoue après tentative, la réponse reste incertaine et les dispatchs sont suspendus jusqu'à reprise.
- Les preuves de test ne sont pas une certification, et la simulation n'offre **aucune déduplication** qui cacherait un double envoi. Le vrai fournisseur, ses scopes, sa normalisation et ses erreurs restent à intégrer. SIGKILL ou panne de machine requièrent encore une supervision de groupe et un nettoyage contrôlé du socket avant redémarrage; ne jamais effacer un socket pouvant appartenir à un service actif.

## Structure

`broker.py` possède le cycle et SQLite; `models.py` et `mime.py` les entrées et le contenu; `policy.py` supervise OPA; `adapters/simulated.py` fournit une unique tentative bornée. MCP et le canal humain ne possèdent pas les règles métier. L'oracle fournisseur est indépendant dans `tests/fixtures/provider_server.py`.

Voir [INTERFACE.md](INTERFACE.md) pour le contrat de développement et [PROVENANCE.md](PROVENANCE.md) pour l'extraction et la traçabilité. Les preuves nouvelles vont dans `pilot-results/codex-email/`, jamais dans les répertoires expérimentaux historiques.
