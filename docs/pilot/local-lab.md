# Laboratoire local de bout en bout

La console permet à l'opérateur et à l'assistant de lire un message fictif via
MCP, préparer une réponse, simuler la décision humaine et observer le MIME reçu.
Broker, OPA et fournisseur HTTP sont de vrais processus locaux. Aucun compte
email, SMTP, OAuth, service distant ou appel de modèle n'est nécessaire au lab.

L'assistant de la session peut manipuler les boutons et rédiger après lecture.
L'étiquette « Assistant IA » décrit cette intervention; elle ne lance pas un
modèle. La campagne automatique utilise des réponses scriptées. Ce sont deux
preuves différentes, toutes deux présentes dans le [rapport](../../pilot-results/local-lab/20260920/REPORT.md).

## Lancer

Depuis `pilots/codex_email/`, après le `./setup.sh` du pilote :

```sh
PYTHONPATH=src:. .venv/bin/python -m lab serve \
  --state-dir /tmp/moraine-lab-demo --port 8790
```

Choisir un dossier neuf, avec un chemin court, hors du dépôt. Le laboratoire
refuse les dossiers existants et les destinations dans ce checkout. Le parent
doit exister. Les limites de chemin des sockets Unix s'appliquent.

Ouvrir `http://127.0.0.1:8790`. Le fichier privé
`/tmp/moraine-lab-demo/connection.json` (0600) contient le jeton à saisir et une
URL de lancement avec fragment. Le fragment est retiré au chargement; le jeton
reste dans le stockage de session du navigateur et passe dans un en-tête HTTP.
Ne pas publier ce fichier ni copier le dossier runtime dans Git. La console
écoute seulement sur loopback et vérifie Host, Origin et authentification.

1. Choisir un mode fournisseur et créer une nouvelle exécution.
2. Lire via MCP, rédiger, proposer, puis charger la revue exacte.
3. Observer zéro tentative avant décision. Approuver ou refuser dans le rôle
   d'opérateur de test. Vérifier les octets reçus et consulter la chronologie.
4. Redémarrer le broker ou révoquer pour observer les effets sur le même état.
5. Lancer les neuf scénarios automatiques; ils utilisent leurs propres services
   et états, sans remplacer l'exécution manuelle affichée.

La proposition conserve sa clé d'idempotence dans l'exécution. La rejouer ne
renvoie pas le message. Modifier son texte après soumission déclenche un conflit;
utiliser une nouvelle exécution pour un autre message de test.

Ctrl-C ou SIGTERM ferme les services créés. Dans la console (`serve`), une
campagne termine son scénario courant avant l'arrêt. En CLI (`run`),
l'interruption arrête le scénario en cours, nettoie ses services et retourne 130;
le résumé de campagne peut rester au dernier point enregistré. Le nettoyage des
groupes de processus est celui du laboratoire, pas une preuve de supervision
systemd. Après arrêt, relancer dans un nouveau dossier. Le dossier précédent
reste disponible pour le diagnostic.

## Campagne sans navigateur

```sh
PYTHONPATH=src:. .venv/bin/python -m lab run \
  --state-dir /tmp/moraine-campaign-demo
```

`--scenario unknown_after_effect --scenario restart` sélectionne des cas.
Le code de sortie est 0 si tout passe, 1 si un scénario échoue, 130 si interrompu.
Les scénarios sont : approbation, refus humain, révocation, expiration réelle,
replay, redémarrage avant décision, refus fournisseur, incertitude après effet
et lecture d'un témoin existant hors de la délégation.

Chaque oracle confronte l'état MCP aux tentatives/effets du fournisseur. Un envoi
accepté exige 1/1 et des octets identiques à la revue; le MIME reçu est aussi
analysé pour vérifier destinataire, expéditeur, sujet, corps et références.
Un refus humain, une expiration ou une révocation avant décision exige 0/0.
Le refus fournisseur exige 1/0; l'incertitude après effet exige `unknown` et 1/1,
y compris après replay/redémarrage. Les nouvelles demandes pour cette source
restent bloquées. Les refus de lecture exigent l'erreur MCP `scope_denied`.

## Observer et diagnostiquer

Dans les dossiers `run-*` initialisés : `report.json` et `events.jsonl` contiennent les
commandes, PID, appels/réponses et assertions sans bearer ni nonce de revue;
`broker.log` et `provider.log` conservent les diagnostics des processus.
`provider/attempts.jsonl` et `effects.jsonl` constituent l'observation indépendante.
`campaign.json` est à la racine du laboratoire CLI, ou sous `campaign-*/` pour
une campagne lancée dans la console. Il résume les scénarios et référence leurs
preuves lorsque l'initialisation a abouti. Si elle échoue, l'entrée peut ne
contenir qu'une erreur; rechercher aussi les diagnostics éventuellement créés
dans `run-*/`. Le démarrage protégé conserve un rapport d'échec et retire ses
enfants; un échec antérieur à cette phase peut ne produire aucun rapport.
Un journal illisible est un échec, jamais une boîte vide ou un succès.

API opérateur : `GET /api/state` et `POST /api/action`, en JSON, avec
`Authorization: Bearer <jeton opérateur>`. Chaque action porte `action` et le
`run_id` affiché (`null` en absence d'exécution). Les actions sont `new` (avec
`actor`, `provider_mode` optionnels), `read`, `propose` (avec `body`), `review`,
`approve`, `reject`, `refresh`, `restart`, `revoke`, `verify`, `campaign`.
Une page obsolète reçoit 409. Ce contrôle est réservé à l'opérateur du lab,
distinct des quatre outils MCP de l'agent. Aucun endpoint ne lit un chemin
arbitraire ou n'exécute une commande fournie par le client.

Deux outils WebMCP facultatifs partagent les boutons de lecture et proposition
lorsque le navigateur supporte `document.modelContext`. Ils n'approuvent rien.
Le navigateur utilisé pour cette livraison ne fournit pas cette API : ces
outils ne sont pas qualifiés; le parcours testé passe par les boutons.

## Portée

Services métier et messages sont locaux; l'IA de cette session ne devient pas un
modèle installé localement. Le rôle humain est simulé pour les tests autorisés.
Les processus partagent le même utilisateur Linux, qui a accès à tous les
fichiers privés. Ni isolation multi-UID/systemd, ni intégration du serveur MCP
dans la configuration Codex, ni ingestion B, ni Prompt Guard, ni livraison email
réelle ne sont qualifiés. Le résultat métier `delivery_status=unverified` reste
inchangé même lorsque le laboratoire observe son propre effet local.
