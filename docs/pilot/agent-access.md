# Demander un accès depuis Codex

Ce parcours utilise un propriétaire, une identité agent stable et deux emails
fictifs. Codex demande l'accès par MCP; l'humain accepte dans son terminal;
Moraine récupère les textes par HTTP auprès du fournisseur simulé. Le grant
permet uniquement la lecture. Une nouvelle conversation retrouve cet accès
par le nom public `travaux-demo`, pendant sa validité de 30 minutes.

Les tests automatisés simulent l'opérateur humain. L'essai Codex utilise aussi
un opérateur de test pour simuler ce canal, sur demande de l'utilisateur;
seuls les appels agent y sont produits par Codex natif. Ce laboratoire
sous un UID ne prouve pas l'isolation OS. Aucun compte email réel, inspection
MIME ou détecteur n'est impliqué.

## Démarrer un runtime neuf

Depuis `pilots/codex_email/`, avec l'environnement du
[guide du pilote](README.md) déjà préparé :

```sh
.venv/bin/python examples/access_demo.py prepare /tmp/moraine-access-demo
.venv/bin/python examples/access_demo.py serve /tmp/moraine-access-demo
```

Le dossier ne doit pas exister avant `prepare`. Il doit rester privé et hors
du dépôt. Le catalogue contient seulement les IDs `upstream-1` et `upstream-2`;
les textes restent chez le fournisseur avant accord. Le message témoin
`upstream-private` n'appartient pas à la sélection.

`serve` affiche l'endpoint MCP et le socket humain. Il garde fournisseur,
broker et OPA en marche et arrête ses propres processus avec Ctrl-C. Les
ports choisis peuvent être occupés entre préparation et démarrage : dans ce
cas, préparer un nouveau runtime sans toucher aux processus étrangers.
Les bases historiques en version 1 sont refusées; aucun upgrade implicite.

## Demander depuis une vraie conversation Codex

Dans un autre terminal, depuis le même dossier :

```sh
.venv/bin/python examples/access_demo.py codex /tmp/moraine-access-demo
```

La commande utilise la CLI Codex déjà connectée. Elle crée une conversation
éphémère avec les outils MCP Moraine, dans un répertoire de travail vide.
Elle consulte `get_access`, soumet `request_access` si aucun accès n'existe,
puis s'arrête si la demande attend l'humain. Elle n'approuve pas la demande.
La sortie JSONL permet d'observer les appels MCP natifs; une déclaration du
modèle seule ne constitue pas une preuve d'appel.

Le lanceur utilise `--ignore-user-config` et des surcharges `-c` limitées au
processus, avec la connexion Codex existante. Il ne modifie pas la configuration
persistante. Le bearer agent est lu depuis un fichier privé et transmis par
variable d'environnement, sans affichage ni argument contenant sa valeur.
Les outils d'envoi ne sont pas exposés à cette démonstration. Le serveur les
conserve pour les autres parcours; la politique refuse de toute façon l'envoi
avec un grant `context_read`.

Configuration MCP vérifiée dans la
[documentation officielle](https://learn.chatgpt.com/docs/extend/mcp) et les
options locales de Codex CLI `0.151.0` le 21 septembre 2026. Le lancement
consomme l'usage de la session Codex existante; il ne demande pas de clé API
de modèle. Les options de la CLI peuvent évoluer.

## Accepter ou refuser par le canal humain

```sh
.venv/bin/moraine-human --socket /tmp/moraine-access-demo/human.sock list-access-requests
.venv/bin/moraine-human --socket /tmp/moraine-access-demo/human.sock review-access REQUEST_ID
```

Lire le périmètre, puis saisir `approve` ou `reject`. Tout autre choix annule
sans décision. La revue expire après cinq minutes et la demande après
30 minutes. Ces délais bornent l'activation, indépendamment de la durée du
grant qui commence à la publication des ressources.

Pour simuler explicitement le rôle humain dans le laboratoire, l'opérateur
de test peut fournir la décision à la même CLI :

```sh
printf 'approve\n' | .venv/bin/moraine-human --socket /tmp/moraine-access-demo/human.sock review-access REQUEST_ID
```

Ce passage traverse réellement revue, digest, nonce et socket authentifié;
il ne démontre pas que l'approbateur est indépendant de l'agent.

L'accord est enregistré avant la récupération. En cas d'échec, l'état reste
`approved` avec `retrieval=failed` et aucun grant. Une nouvelle tentative
demande une nouvelle clé et une nouvelle décision. Une consultation ne
relance jamais le fournisseur. Une autre clé visant une demande en attente
ou un accès actif reçoit `access_already_exists`; cette clé refusée n'est pas
consommée. Consulter `get_access` pour retrouver l'existant.

## Lire et reprendre dans une autre conversation

Relancer la commande `codex` : avec l'accès actif, la conversation retrouve
le grant par `get_access`, puis utilise `list_context` et `read_context`.
Relancer encore pour observer une autre conversation avec le même grant,
sans transmettre son identifiant dans le prompt. Garder le runtime en marche.
On peut aussi redémarrer `serve` sur le même runtime en version 2 : les
décisions et captures restent disponibles, sans récupération automatique.

Comparer indépendamment `provider/reads.jsonl` avec les métadonnées retournées :
un seul appel, les deux IDs attendus et les mêmes `source_digest`. Ces digests
portent sur le JSON canonique reçu; le digest de ressource couvre la capture
locale versionnée et n'est pas le digest MIME du chemin d'envoi.

Après lecture, révoquer dans le terminal humain :

```sh
.venv/bin/moraine-human --socket /tmp/moraine-access-demo/human.sock revoke-grant GRANT_ID
```

Une consultation indique `revoked`; les nouvelles lectures sont refusées.
La révocation ne rappelle pas les textes déjà reçus. Arrêter `serve` par Ctrl-C
à la fin. Garder jetons, bases et logs privés hors Git; exporter uniquement les
preuves nécessaires et expurgées.

## Contrôles automatisés

Depuis `pilots/codex_email/` :

```sh
.venv/bin/python -m pytest tests/test_access.py tests/test_access_process.py -q
./test.sh -q
```

Ces tests couvrent capture HTTP, refus, échéances, droits, réponses invalides,
idempotence, concurrence, interruption, panne de publication et redémarrages.
Le test de processus traverse la CLI humaine avec une réponse scriptée;
cela ne remplace pas une décision manuelle.
