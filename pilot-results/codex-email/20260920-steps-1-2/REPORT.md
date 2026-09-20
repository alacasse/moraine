# Développement local du pilote email — 20 septembre 2026

Les étapes 1–2 du [plan](../../../docs/plans/codex-mcp-email-pilot.md) sont implémentées dans [pilots/codex_email](../../../pilots/codex_email/README.md), sur fournisseur simulé. Le dépôt a été initialisé et l'existant conservé dans le commit `5feab54a15716b2ca352357c1c0b58c5f4089c84`, avec attribution Codex. À l'issue de cette validation, le développement et ce rapport étaient laissés dans l'arbre de travail, sans commit supplémentaire ni publication. L'utilisateur a ensuite demandé leur commit et la publication du projet dans un dépôt GitHub public.

## Résultat

Le broker OPA/SQLite conserve les délégations immuables, prépare une seule fois les octets MIME et exige une décision humaine liée au digest et au nonce. Les quatre outils MCP ne permettent aucune approbation. Le socket Unix humain authentifie le pair par `SO_PEERCRED`. Les intentions durables, résultats incertains et replays sont traités sans retransmission automatique; révocation et expiration empêchent de nouvelles divulgations sans réécrire les résultats terminaux.

Le fournisseur simulé journalise séparément tentatives et effets, sans déduplication. Le parcours en processus distincts utilise le SDK MCP officiel sur TCP, ferme le client, redémarre le broker avec une demande en attente, approuve par socket humain et compare les octets reçus au snapshot. Une répétition produit toujours une seule tentative et un seul effet; après révocation, le résultat terminal est conservé avec projection réduite.

## Validation et preuves

- **64 tests réussis, 2 avertissements, 18,50 s** : [journal](tests.log), [JUnit](tests.xml), [commande et portée](execution.json). Le script exécute aussi `opa check --strict` et `opa test`; il n'y a pas de tests Rego natifs dans ce pilote, les cas de politique passent par les tests Python avec OPA réel.
- Les suites couvrent notamment refus avant lecture protégée, identités et bornes, échéances pendant attente, nonce/digest, rejets humains, concurrence et replay, reprise d'intention, panne du commit après effet, barrière d'incertitude entre grants et masquage après révocation.
- [Transcription du parcours réel local](process/transcript.json), [tentatives observées](process/attempts.jsonl), [effets observés](process/effects.jsonl), et journaux des processus dans `process/`. Données fictives uniquement; jetons, configuration privée et bases SQLite ne sont pas archivés.
- [Manifest des sources du pilote](source-manifest.json), [versions exécutées](runtime.json), [vérifications finales](verification.json). Les 66 fichiers du manifest historique correspondent encore; aucune modification Git suivie sous `experiments/` ou `docs/experiments/`.
- Les deux avertissements concernent le client de test Starlette avec HTTPX et un alias AnyIO déprécié. Le verrou de dépendances courant est également résolu par `uv sync --frozen --offline`; aucun changement de dépendance n'est déduit de ces avertissements.

Les tests nécessitent l'ouverture de sockets Unix/TCP loopback. Leur exécution a utilisé une permission d'exécution élargie, le sandbox ordinaire bloquant ces sockets. Les dépendances publiques ont été acquises séparément avec permission réseau; les versions et empreintes sont verrouillées. Aucun compte réel n'a été utilisé.

## Répartition et contre-revues

`pilot_core` a implémenté broker, politique et tests associés; `pilot_transports`, les façades MCP/humain et leurs tests. Le coordinateur a fourni modèles, MIME, adaptateur/oracle simulé, intégration et parcours en processus. Les reviewers n'ont pas validé seuls leurs propres composants : `review_pilot` a examiné le cœur et l'intégration; `pilot_core` a ensuite examiné les transports de l'autre auteur.

| Constat | Correction | Vérification |
|---|---|---|
| Timeout HTTP par lecture insuffisant pour borner toute la tentative | Budget global de quatre secondes couvrant connexion, écriture, en-têtes et corps; zéro retry | Régression serveur à en-têtes lents et confirmation indépendante |
| Bornes JSON trop petites après échappement des textes autorisés | Enveloppe humain 1 Mio, MCP 128 Kio; bornes logiques conservées | Unicode/contrôles au maximum et dépassement logique, socket humain réel; relecture indépendante |
| Bearer pouvant expirer pendant lecture/attente/verrou | Contrôles après réception, avant file de travail et après acquisition du verrou | Reproductions originales réexécutées et nouvelles régressions |
| Confusion visuelle entre contrôle et séquence littérale échappée | Antislashs également échappés dans la présentation humaine | Régressions de rendu et contre-revue ciblée |
| SIGTERM laissant socket humain et OPA actifs | Déroulement du nettoyage lors de l'arrêt du lanceur | Parcours en processus : arrêt gracieux puis reprise sur le même socket/état |

Les deux reviewers ont confirmé la résolution de leurs constats ciblés, sans constat bloquant restant pour les étapes 1–2. La suite complète finale a été exécutée par le coordinateur. La contre-revue des bornes et du test processus était une relecture; elle ne constitue pas une seconde exécution de toute la suite.

## Limites et suite

La preuve porte sur un utilisateur Linux unique, des textes fictifs et un fournisseur local. Elle ne valide ni séparation de comptes OS, ni confinement des autres outils de Codex, ni client Codex réel, ni OAuth/Gmail ou livraison. Le parcours processus valide une reprise après arrêt gracieux, pas un crash au milieu d'un dispatch. Les tests ciblés d'intention et de commit ne remplacent pas une campagne de pannes machine. L'absence de descendants OPA orphelins n'est pas une assertion exhaustive de ce parcours.

L'étape 3 devra établir utilisateurs/groupes, chemins et secrets protégés, supervision du groupe de processus, nettoyage contrôlé après SIGKILL et sondes de contournement depuis le vrai client Codex. Les étapes suivantes devront intégrer le fournisseur et confirmer les pouvoirs du compte puis la réception réelle. Aucun service permanent, utilisateur système, configuration Codex ou compte email n'a été installé par cette livraison.
