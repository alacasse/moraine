# Demande d'accès agent — validation locale

Date : **21 septembre 2026**. Workspace dérivé de
`6e5a48372d74fa35d3709b041f22ce8a6e371348`, sans commit ni push.
Le [plan](../../../docs/plans/agent-access-pilot.md) a été autorisé après sa
[revue indépendante](../../agent-access/20260921-plan-review/REPORT.md).

## Implémentation

`request_access` persiste la demande; `get_access` retrouve l'état et le grant
par nom de sélection. L'humain décide par socket Unix sur digest/nonce. Après
accord, Moraine récupère les deux messages fictifs par HTTP, valide le lot et
publie grant de lecture, captures et disponibilité dans une seule transaction.
Ce grant ne permet aucune proposition d'envoi.

Refus, panne, réponse invalide, échéance dépassée et interruption ne publient
aucun accès. Consultation et redémarrage ne relancent pas le fournisseur.
Le lanceur configure MCP uniquement pour le processus Codex de l'essai.
Les parcours d'envoi existants restent testés.

Les précisions de revue sont intégrées : conflit sans consommation de la
nouvelle clé lorsqu'un accès existe déjà; résultat `approved/failed` et rollback
si l'échéance passe pendant récupération ou publication. Le stockage utilise
la version 2; les bases v1 sont refusées sans migration.

## Tests exécutés

Depuis `pilots/codex_email/`, avec sockets Unix/TCP loopback autorisés :

| Commande | Résultat observé |
| --- | --- |
| `.venv/bin/python -m pytest tests/test_lifecycle.py tests/test_mcp.py tests/test_policy.py -xq` | 37 passed, 2 warnings, 5.54 s |
| `.venv/bin/python -m pytest tests/test_access.py -xq` | 15 passed, 9.98 s, avant les cas supplémentaires |
| `.venv/bin/python -m pytest tests/test_access_process.py -xq` | 1 passed, 3.52 s |
| `./test.sh -q`, première suite complète | OPA check/test puis 121 passed, 2 warnings, 60.39 s |
| `./test.sh -q`, code final | OPA check/test puis **122 passed**, 2 warnings, 61.06 s |

Les avertissements sont les dépréciations Starlette/httpx et AnyIO BlockingPortal.
Le premier essai sans sockets avait échoué au démarrage d'OPA et a été arrêté;
les résultats ci-dessus proviennent des exécutions avec sockets autorisés.
Aucune dépendance n'a été ajoutée.

Les contrôles documentaires vérifient les chemins/ancres et analysent les blocs
shell avec `bash -n` sans exécution. Les 51 sources archivées correspondent
aux fichiers du workspace; l'empreinte de l'archive est vérifiée.

Le test de processus traverse fournisseur, broker/OPA, client MCP officiel
et CLI humaine. Il vérifie demande durable, redémarrages avant décision et
après publication, digests observés chez le fournisseur, lectures puis refus
après révocation. **L'opérateur humain y est simulé par le test.**

## Codex natif et canal humain simulé

La conversation `01a0c4d1-0945-7331-a3ef-24c569b338e9` a appelé nativement
`moraine.get_access`, puis `moraine.request_access`. La demande
`8c9f1c61-f432-45e2-8c4d-81e00a350e31` a été persistée `pending/not_started`,
sans grant, ressource publiée ou lecture fournisseur. Aucun shell ni lecture
de fichier n'a été exécuté par cette conversation pour ce parcours.

L'utilisateur a ensuite précisé que **le canal humain devait être simulé**.
L'opérateur de test a exécuté `review-access` avec `approve` dans la vraie CLI,
qui traverse le socket authentifié et consomme le nonce de la revue. Le résultat
est `approved/ready`, avec le grant `0aac6dd3-408d-4041-b004-935f5b02a6b7`.
Cela ne prouve pas un consentement humain indépendant.

Deux conversations Codex distinctes ont ensuite retrouvé et lu ce même grant :

| Conversation | Appels MCP natifs observés |
| --- | --- |
| `01a0c4db-1710-7573-89d1-ecb5c95b1c76` | `get_access`, `list_context`, deux `read_context` |
| `01a0c4db-bfee-7612-ac14-168ec8b15ea7` | `get_access`, `list_context`, deux `read_context` |

Aucune nouvelle demande ni approbation entre ces lectures. Les deux réponses
mentionnent la visite mardi à 10 h, le garage à dégager et le budget fictif
de 240 euros. Les sorties JSONL prouvent les appels MCP réels, sans commande
shell ni lecture de fichier par ces conversations.

Le journal fournisseur contient **une seule récupération** des deux IDs, dont
les digests correspondent aux métadonnées lues. Le témoin exclu n'est ni demandé
ni publié. La base contient une demande, un grant et deux captures; aucun envoi.

Pour finir, l'opérateur a révoqué le grant par le canal humain simulé. Le client
MCP officiel a observé `get_access=revoked`, puis `scope_denied` pour
`list_context` et `read_context`, sans nouveau fetch. Ce dernier contrôle est
scripté, distinct des lectures Codex natives. Le runtime a été arrêté et son
socket retiré; seuls ses fichiers privés sont conservés hors dépôt.

## Preuves et limites

- [Demande Codex](codex-request.json) et [état avant accord](observations.json).
- [Canal humain simulé](human-simulated.txt), [première lecture Codex](codex-read-first.json)
  et [seconde lecture Codex](codex-read-second.json).
- [Comparaison des lectures et du fournisseur](native-checks.json) et
  [contrôles après révocation](revocation-checks.json).
- [Sources du pilote](source.zip) et [manifeste](manifest.json) : empreintes de
  l'arbre testé, fichiers nouveaux non commités inclus.
- [Mode opératoire](../../../docs/pilot/agent-access.md).

Jetons, `connection.json`, bases et logs privés restent hors Git. L'archive
porte sur les sources du pilote, sans dépendances installées. Les preuves
antérieures restent inchangées. Un seul UID ne prouve pas le confinement OS.
Le fournisseur JSON est fictif; aucun MIME entrant, détecteur, compte distant
ou envoi réel n'est qualifié. Aucun réglage Codex persistant n'a été modifié.
