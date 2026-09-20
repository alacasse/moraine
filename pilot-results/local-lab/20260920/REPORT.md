# Laboratoire local — validation du 20 septembre 2026

Le laboratoire permet à l'assistant de manipuler le parcours dans le navigateur,
d'observer les réponses MCP et les effets indépendants, puis de reproduire les
erreurs sans compte fournisseur. Les services métier sont locaux. L'assistant
intervient dans sa session existante; aucun modèle embarqué ou appel API de
modèle n'est ajouté au projet.

Base Git : `f4350fe37d285598ebe5ef9e3253ac2af12e3b35`.
Branche : `codex/local-e2e-lab`, modifications non commitées/non poussées.
Le manifeste `manifest.json` fige les empreintes des sources et des preuves;
le SHA de base seul ne désigne pas le nouveau laboratoire.

## Résultats

- Suite complète via `./test.sh -q` : **102 passed, 2 warnings, 45.61 s**.
  Les 96 tests existants restent verts; six tests ajoutent campagne réelle,
  frontières HTTP, échec partiel de démarrage, requête retardée à l'arrêt,
  confinement du runtime et diagnostic de preuve illisible.
- Campagne finale lancée par le bouton de la console : **9/9 réussis**.
  Voir `campaign.json` et les rapports sous `scenarios/`.
- CLI `run --scenario unknown_after_effect --scenario restart` : **2/2 réussis**,
  code de sortie 0. Voir `cli-campaign.json` et `cli-final.log`.
- Parcours assistant final : lecture MCP, rédaction à partir du texte lu,
  proposition, observation `pending`/0/0, revue, approbation simulée puis
  `accepted`/1/1. Trois vérifications réussies : comptes, égalité des octets
  revus/reçus, et champs/contenu du MIME. Voir `assistant/` et
  [capture finale](assistant-delivery.png).
- Refus manipulé au navigateur : `rejected`, aucune tentative, aucun effet.
  Voir `browser-rejection/`.
- Déconnexion après effet manipulée au navigateur : `unknown`, une tentative,
  un effet réel. Le MIME contient les balises hostiles littérales; aucun élément
  HTML injecté ni exécution du marqueur JavaScript dans la revue ou la réception.
  Voir `browser-unknown/` et captures [bureau](uncertain-desktop.png) /
  [mobile](uncertain-mobile.png).
- Console navigateur : aucune erreur ni avertissement JavaScript observé;
  aucune largeur débordante à 1440 et 390 px. API WebMCP absente du navigateur :
  les deux outils facultatifs ne sont pas qualifiés. Les boutons ont été testés.

Les deux avertissements pytest concernent Starlette/httpx et un alias AnyIO
dépréciés, déjà présents avant ce lot. OPA `check --strict` et `test` ont retourné
0 via `test.sh`; les attentes de politique sont exercées par les tests Python.

| Scénario | État final attendu et observé | Tentatives / effets |
| --- | --- | --- |
| Approbation | `accepted` | 1 / 1 |
| Refus humain simulé | `rejected` | 0 / 0 |
| Révocation avant décision | `denied`, `grant_revoked` | 0 / 0 |
| Expiration réelle | `denied`, `grant_expired` | 0 / 0 |
| Replay | identité conservée, `accepted` | 1 / 1 |
| Redémarrage avant décision | demande conservée, puis `accepted` | 1 / 1 |
| Refus fournisseur | `failed`, `provider_rejected` | 1 / 0 |
| Déconnexion après effet | `unknown`, `provider_outcome_unknown` | 1 / 1 |
| Lecture hors délégation | MCP `scope_denied`, aucun contenu retourné | 0 / 0 |

Le témoin hors délégation existe sous un autre grant; une lecture autorisée
précède son refus. Pour `unknown`, le test prépare aussi une seconde demande
avant l'incident, vérifie son blocage, le replay sans effet additionnel, la
persistance après redémarrage et le blocage sous nouvelle clé/nouveau grant.
Révocation et expiration refusent la lecture par `scope_denied` et exposent
seulement les trois champs du reçu terminal à l'agent.

## Corrections et revue indépendante

La première campagne a échoué sur une attente du banc : la seconde demande
préexistante était bien bloquée, mais par `source_unresolved`, pas par
`dispatch_denied`. Vérification du chemin `execute_guard`, correction de
l'oracle et réexécution ont conservé l'exigence 1/1. Aucun changement du broker.

Deux reviewers indépendants ont examiné les oracles/livraison et les frontières
d'autorité/cycle de vie. Trois P2 corrigés, contre-revues clôturées sans constat
actionnable restant :

1. Les refus après expiration/révocation exigent précisément `scope_denied`;
   une erreur technique ne peut plus compter comme preuve attendue.
2. L'arrêt pose une barrière sous le verrou commun avant nettoyage. Un vrai
   POST déjà accepté, mais dont le corps arrive après fermeture, reçoit 409
   et ne recrée aucun processus. Sonde indépendante et régression locale.
3. Une destination runtime dans le checkout est refusée avant création; un
   dossier existant n'est jamais réutilisé.

Le cas de journal fournisseur illisible conserve un diagnostic et des comptes
inconnus, ferme les services et échoue. Le cas de démarrage partiel conserve
le journal du broker, retire le fournisseur déjà lancé et permet une nouvelle
exécution. Les preuves ne transforment pas ces incidents en succès silencieux.

## Reproduire et poursuivre

Voir le [guide du laboratoire](../../../pilots/codex_email/lab/README.md).
La console finale est démarrée sur `http://127.0.0.1:8790`, avec son runtime privé
dans `/tmp/moraine-lab-20260920-final`. Elle est disponible tant que ce processus
reste actif. `connection.json` y remet le jeton opérateur; il n'est pas exporté.
Le rapport `assistant/report.json` fige un instant, pas une surveillance continue
des PID qui y figurent.

Les exports incluent seulement rapports expurgés et journaux indépendants des
tentatives/effets; aucun bearer, nonce, fichier de connexion ou base SQLite.
Les captures `unknown` viennent de l'itération navigateur précédente, avant les
corrections de fermeture et de confinement; le JS/CSS et ce parcours n'ont pas
changé entre ces captures et la validation finale.

Ce résultat valide le protocole applicatif et l'observation du fournisseur
simulé. Il ne qualifie pas systemd, des UID distincts, l'installation du serveur
MCP dans Codex, l'ingestion B, Prompt Guard, OAuth/Gmail ou une livraison email
réelle. L'opérateur de test joue les deux rôles. Le reçu métier conserve
`delivery_status=unverified`, même si le laboratoire constate son effet local.
