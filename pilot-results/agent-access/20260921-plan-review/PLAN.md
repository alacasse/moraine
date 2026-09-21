# Premier parcours agent : demander un accès et lire des emails simulés

Date : **21 septembre 2026**. **Périmètre de l'expérience accepté; plan
d'implémentation proposé. Aucun développement autorisé par ce document.**

Ce plan prolonge l'[exploration côté agents](../prompts/explore-agent-moraine.md)
et la [note sur la délégation](../research/delegation-ux-multi-provider.md).
Le code a été examiné sur `master`, à
`6e5a48372d74fa35d3709b041f22ce8a6e371348`. Les constats ci-dessous viennent
de sa lecture, pas d'une nouvelle exécution du pilote.

## 1. Ce que nous voulons observer

Un utilisateur demande à Codex de travailler sur quelques emails fictifs.
Codex demande l'accès à Moraine; Moraine conserve cette demande en base.
L'utilisateur l'accepte localement. Moraine récupère alors les messages par
l'API d'un fournisseur simulé, puis Codex les lit avec les outils Moraine.

Le même agent doit retrouver l'accès depuis une autre conversation. Le droit
appartient à l'identité reconnue par Moraine; sa validité ne dépend pas de la
mémoire d'une conversation. Le mécanisme général d'association des agents aux
utilisateurs reste à concevoir.

**Choix exprimés par l'utilisateur :** commencer avec Codex et un fournisseur
email simulé; enregistrer une véritable demande d'accès; accepter localement
en contournant seulement la notification/application mobile. Le pilote sert
à découvrir les responsabilités avec un utilisateur. La montée en charge et
une éventuelle réécriture viendront des découvertes, sans objectif de millions
d'utilisateurs dans ce lot.

**Bornes proposées pour cette expérience :** un propriétaire, une identité
agent configurée, un compte fictif, deux messages sélectionnés et un message
témoin exclu. Lecture seule, sélection immuable, sans filtre vivant ni nouveaux
messages ajoutés automatiquement. Garder la borne technique actuelle de
30 minutes pour l'accès, sans faire choisir une durée à l'humain. Elle ne
tranche pas la politique produit d'accès continu ou temporaire.

## 2. Ce que le pilote fournit déjà

| Socle vérifié | Écart à combler |
| --- | --- |
| [MCP HTTP local](../../pilots/codex_email/src/moraine_email/mcp_server.py), bearer associé à une identité agent configurée, quatre outils stricts | Ajouter la demande d'accès et sa consultation; brancher un vrai client Codex |
| [Broker SQLite](../../pilots/codex_email/src/moraine_email/broker.py), grants persistants, ressources versionnées, lecture contrôlée | La table `requests` décrit les propositions de réponse email, pas les demandes d'accès |
| [Canal humain Unix](../../pilots/codex_email/src/moraine_email/human_server.py) et [CLI](../../pilots/codex_email/src/moraine_email/human_cli.py) | Ajouter la présentation et la décision propres à une demande d'accès |
| [Validation des grants](../../pilots/codex_email/src/moraine_email/models.py) et [politique OPA](../../pilots/codex_email/src/moraine_email/policy/broker.rego) | Les grants actuels exigent une cible de réponse; introduire explicitement la lecture seule |
| [Adaptateur simulé](../../pilots/codex_email/src/moraine_email/adapters/simulated.py) et [serveur fournisseur](../../pilots/codex_email/tests/fixtures/provider_server.py) séparé | Seul l'envoi est implémenté; ajouter une API de récupération de messages fictifs |
| [Laboratoire](../../pilots/codex_email/lab/runtime.py) et [client MCP scripté](../../pilots/codex_email/examples/agent_client.py) | Le lab fournit lui-même les textes au grant; ce raccourci ne doit pas constituer la preuve du nouveau parcours |

Il faut donc compléter le chemin existant, sans construire un framework
d'adaptateurs, un service multiutilisateur ou une nouvelle interface web.

## 3. Parcours minimal proposé

1. L'opérateur démarre un runtime privé neuf et le fournisseur local. Seul le
   fournisseur détient les corps des messages. Moraine connaît une sélection
   de démonstration, `travaux-demo`, et ses deux identifiants fournisseur.
2. Une session Codex dispose du connecteur MCP Moraine et de ce nom public de
   sélection. Elle consulte l'accès, puis soumet une demande s'il manque.
3. Moraine fige la sélection et enregistre la demande `pending`. Codex reçoit
   sa référence et son état, sans sujet, expéditeur, aperçu ni corps d'email.
   L'appel termine immédiatement; il n'attend pas l'humain.
4. Dans son terminal, l'utilisateur consulte les demandes et ouvre celle-ci.
   Moraine présente l'agent, le compte fictif, les IDs sélectionnés, le droit
   de lecture, sa durée et l'absence d'inclusion de futurs messages. L'utilisateur
   accepte ou refuse par le canal humain existant.
5. En cas d'accord, Moraine persiste la décision, puis appelle le fournisseur.
   Après validation de la réponse et nouveau contrôle de validité, il publie
   atomiquement le grant de lecture, les ressources et le résultat disponible.
6. Codex consulte l'état. Dès que les données sont disponibles, il utilise
   `list_context` puis `read_context` avec le grant retourné.
7. Une seconde conversation Codex, avec la même identité configurée, retrouve
   ce grant en consultant `travaux-demo`. Elle lit les captures existantes
   sans nouvelle approbation ni nouvelle récupération fournisseur, tant que
   l'accès reste actif.

La démonstration se termine par une révocation humaine et une lecture refusée.
Révoquer empêche les lectures suivantes; cela n'efface pas les données déjà
reçues dans une conversation.

## 4. Contrat étroit à ajouter

Les noms ci-dessous sont proposés pour ce lot; le contrat maintenu sera mis
à jour avec l'implémentation.

### Côté agent

| Outil | Entrée | Résultat permis |
| --- | --- | --- |
| `request_access` | `resource_set_ref`, `idempotency_key` | Référence de demande et état; aucune autorité ni donnée email |
| `get_access` | `resource_set_ref` | Dernière demande de cet agent pour cette sélection, décision, disponibilité et état actuel de l'accès; grant utilisable lorsqu'il est actif |
| `list_context`, `read_context` | Contrat existant | Métadonnées puis texte des ressources autorisées |

`get_access` résout la reprise entre conversations sans imposer de recopier
un identifiant issu de la première. Il consulte uniquement le nom public
configuré; il n'énumère ni comptes ni boîtes de messagerie. Pour une sélection
connue sans demande, il retourne un état d'absence sans créer de ligne.

L'identité, le compte, les IDs exacts, les droits et les durées sont déterminés
par Moraine. Les champs supplémentaires, notamment `agent`, `approved`, URL
ou texte à publier, sont refusés. Une référence inconnue ou inaccessible ne
révèle pas l'existence d'une sélection d'un autre acteur.

### Demande persistante et décision humaine

Créer une table dédiée `access_requests`; conserver `requests` et `decisions`
dans leur rôle actuel d'approbation d'envoi. Une ligne contient au minimum :
identité authentifiée, clé d'idempotence, référence publique, périmètre figé
et digest, horodatages/échéances, décision humaine, état de récupération et
référence éventuelle du grant. Aucun corps email dans la demande en attente.

Les états distinguent deux faits :

| Décision | Récupération | Sens |
| --- | --- | --- |
| `pending` | `not_started` | Aucun accord et aucun appel fournisseur |
| `rejected` ou `expired` | `not_started` | Aucun accès créé |
| `approved` | `fetching` | Accord conservé; données encore indisponibles |
| `approved` | `ready` | Capture et grant publiés ensemble |
| `approved` | `failed` | Accord conservé; échec de récupération, aucun grant |

L'état courant du grant (`active`, `expired`, `revoked`) est calculé lors de
la consultation. Une ancienne réussite ne doit pas apparaître comme un accès
encore utilisable après expiration ou révocation.

Proposer des opérations humaines distinctes : liste des demandes, revue d'une
demande, acceptation/refus. La CLI affiche un résumé produit par Moraine et
renvoie le digest et un nonce liés à cette revue, avec une échéance technique.
Le périmètre ne peut plus changer après soumission. Modifier le catalogue
local ne modifie ni la demande examinée ni un grant existant. Ne pas réutiliser
le snapshot MIME ou les décisions d'envoi pour cet accord de lecture.

Pour borner ce pilote, proposer une attente maximale de 30 minutes et une
revue valable 5 minutes, sans dépasser l'échéance de la demande. Vérifier
l'échéance avant récupération et avant publication. Les 30 minutes du grant
commencent à sa publication; ce délai reste distinct de celui de la demande.

Même identité + même clé + même contenu : même demande, aucun nouvel effet.
Même clé avec un contenu différent : conflit explicite. Une demande déjà en
attente ou un accès actif sur le même périmètre est signalé sans créer une
seconde sollicitation. Un second clic d'approbation ne lance pas une seconde
récupération. Après échec ou refus, une nouvelle tentative nécessite une
nouvelle demande et une nouvelle décision.

### Lecture seule et récupération

Introduire un type explicite de grant, `context_read` ou `reply`. Adapter
directement les producteurs actuels, validateurs, consommateurs et règles OPA.
Un grant `context_read` n'a pas de destinataire ni de cible de réponse.
`propose_reply` doit le refuser avant d'accéder à ces champs, sans créer de
proposition d'envoi. Les grants `reply` gardent leur parcours actuel.

Ajouter une opération étroite à l'adaptateur simulé : récupérer la liste
fermée des IDs approuvés. Le fournisseur sert des objets JSON fictifs avec
texte et métadonnées; aucun MIME réel, HTML, attachement, lien suivi ou secret
de messagerie réelle. Le jeton fournisseur reste propre au broker.

Conserver les propriétés du transport local : origine loopback configurée,
absence de redirection et de retry, délai global borné. Proposition : un
appel pour la sélection, 4 secondes au total, réponse limitée à 256 Kio avant
décodage; conserver ensuite les bornes de champs et de textes du pilote.
Refuser le lot entier en cas d'ID absent, supplémentaire, dupliqué, de contenu
invalide ou de dépassement. Moraine attribue les références locales, versions
et digests aux captures validées; le fournisseur ne fournit aucun droit.

La décision est persistée avant l'IO; aucune transaction SQLite ne reste
ouverte pendant l'appel. Une exécution synchrone bornée dans le chemin humain
suffit au pilote, sans file de travaux ni daemon supplémentaire. Garder la
sérialisation du broker et recontrôler les échéances avant publication.
Le grant, ses ressources et `ready` sont écrits dans une seule transaction.

Après redémarrage, les demandes en attente et les résultats finalisés restent
consultables. Une récupération interrompue devient `failed`, sans reprise
automatique; une consultation ne déclenche jamais d'IO fournisseur. Ce résultat
de lecture est distinct du `unknown` d'envoi et ne change pas ses barrières.

Prévoir une nouvelle version du stockage et un runtime neuf. Ne pas migrer
automatiquement les anciennes bases de démonstration ni leur attribuer un
type de grant implicite; préserver ces bases comme preuves de leur version.

## 5. Ordre d'implémentation proposé

| Étape | Travail et fichiers principaux | Preuve attendue avant la suite |
| --- | --- | --- |
| 1. Demande et lecture seule | `models.py`, `broker.py`, `policy/broker.rego`; table dédiée, états, idempotence, grants typés | Demande durable; refus d'une proposition d'envoi avec un grant de lecture; parcours d'envoi existant préservé |
| 2. Décision et capture | `human_server.py`, `human_cli.py`, `adapters/simulated.py`, `tests/fixtures/provider_server.py` | Acceptation authentifiée puis appel HTTP réel; publication atomique; refus/échec sans grant |
| 3. Parcours MCP complet | `mcp_server.py`, exemple de client dédié et tests de processus | Demande, attente, décision locale, consultation et lecture à travers les vrais transports |
| 4. Essai Codex | Petit lanceur de démonstration et guide d'utilisation | Outils Moraine invoqués nativement dans Codex, puis accès retrouvé dans une seconde conversation |

Ces étapes forment un seul lot local. Conserver les tests et scénarios d'envoi
existants; le nouveau lanceur initialise la sélection par IDs, sans appeler
`create_grant` avec des textes copiés. Le fournisseur produit un journal de
lecture indépendant indiquant les IDs demandés et les digests retournés.

Pour Codex, la CLI installée au moment du plan est `0.151.0`. Son aide locale
confirme MCP HTTP avec bearer par variable d'environnement et les surcharges
de configuration `-c`. Préparer une session dédiée avec configuration limitée
au processus; vérifier le raccordement effectif au moment de l'essai. Aucune
configuration n'a été changée pour ce plan. La
[documentation officielle MCP](https://learn.chatgpt.com/docs/extend/mcp)
est une référence de branchement, pas une preuve de compatibilité Moraine.

Le lanceur devra charger le bearer agent depuis un fichier privé sans l'afficher;
aucun jeton dans Git, les arguments en clair, les prompts ou les exports de
preuve. Il conserve le runtime entre les deux conversations. Il ne présume
pas qu'ajouter un serveur rend ses outils disponibles dans une session déjà
ouverte. Toute future modification persistante sous le Codex home doit suivre
la résolution de propriétaire prévue par les consignes applicables.

## 6. Critères d'acceptation observables

| Cas | Oracle attendu |
| --- | --- |
| Première demande | Une ligne durable `pending`; zéro lecture dans le journal fournisseur; aucune donnée email retournée à l'agent |
| Répétition/reprise | Même demande pour un retry identique, conflit si contenu changé; aucune duplication après redémarrage |
| Refus ou expiration avant accord | Aucun grant, aucune ressource publiée, zéro lecture fournisseur |
| Accord puis succès | Décision humaine persistée; un seul appel fournisseur pour les deux IDs; données publiées correspondant aux digests observés chez le fournisseur |
| Réponse perdue ou double approbation | Consultation du résultat enregistré, sans second appel fournisseur ni seconde publication |
| Fournisseur absent, lent ou invalide | `approved` + `failed`, motif fermé sans contenu fournisseur; aucun grant ni publication partielle |
| Arrêt pendant la récupération | Après relance, échec explicite sans retry automatique et sans grant partiel |
| Témoin hors sélection | Son ID n'est pas demandé au fournisseur; ses métadonnées et son texte n'apparaissent dans aucune réponse agent |
| Extension ou usurpation | Champs d'autorité supplémentaires rejetés; demande ou grant d'une autre identité inaccessibles; IDs/URL arbitraires refusés |
| Lecture seule | `propose_reply` refusé pour le nouveau grant, aucune proposition ni aucun envoi fournisseur |
| Deuxième conversation Codex | Même identité, même grant retrouvé par `get_access`, lecture réussie sans nouvel accord ni nouvel appel fournisseur |
| Révocation ou expiration de l'accès | État actuel visible; `list_context` et `read_context` refusés, aucun rafraîchissement implicite |

Les tests automatisés doivent traverser les processus MCP, broker, socket
humain, OPA et fournisseur. Le script simule alors l'opérateur humain; le
rapport le dit explicitement. Une preuve séparée utilise les outils natifs
d'une session Codex avec décision manuelle de l'utilisateur. Le seul client
MCP Python ne suffit pas à qualifier cette intégration Codex.

Lors du développement, exécuter les tests ciblés des comportements modifiés,
puis `./test.sh -q` depuis `pilots/codex_email/` pour la validation finale OPA
et pytest. Utiliser `./setup.sh` seulement si l'environnement manque. Conserver
un rapport daté indiquant le commit testé, les commandes, les résultats, les
limites et les références d'exports expurgés. Aucun de ces tests n'a été lancé
pour rédiger ce plan.

## 7. Limites, documentation et livraison

Le runtime reste privé, neuf et hors dépôt; les preuves antérieures restent
intactes. N'arrêter que les processus créés pour cet essai. Ne conserver dans
les preuves que les exports nécessaires, sans jetons, bases brutes ou journaux
privés. L'expérience sous un seul UID valide un protocole et des états;
elle ne démontre pas que Codex est incapable d'atteindre le canal humain ou
les fichiers du fournisseur par d'autres outils. L'isolation Linux reste une
qualification séparée.

Ce fournisseur JSON fictif sert à observer les responsabilités. Il ne réalise
pas le [contrat proposé d'ingestion](email-ingestion-contract.md), ne qualifie
aucun inspecteur et ne rend pas des emails réels publiables. Les fixtures
restent des données; un marqueur fourni par l'agent ne peut pas activer ce
profil. La capture MIME, l'inspection et la politique de publication pour
des contenus réels demandent leur propre travail.

Mettre à jour avec le code l'[interface](../pilot/interface.md),
l'[architecture](../architecture.md), le [guide du pilote](../pilot/README.md)
et l'[état du projet](../status.md). Ajouter le mode opératoire de ce parcours
et distinguer preuve scriptée, essai Codex et validation d'isolation.
La mention actuelle des « quatre outils MCP » dans
[AGENTS.md](../../AGENTS.md) devra évoluer si les nouveaux outils sont retenus;
sa modification exige une autorisation explicite nommant ce fichier, selon
ses règles de propriété. Ce plan ne le modifie pas.

Restent ouverts pour le produit : association de plusieurs agents, accès
continu, découverte des ressources, périmètres évolutifs, notifications,
gestion mobile/web, intégrations ChatGPT et autres clients, fournisseurs réels
et passage à plusieurs utilisateurs. Ils ne sont pas des prérequis à cette
expérience. La prochaine décision porte sur ce lot proposé; son implémentation,
sa configuration effective et sa publication ne sont pas engagées ici.
