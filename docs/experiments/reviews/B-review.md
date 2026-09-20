# Revue indépendante B — broker OPA

Date : 2026-09-20. Mode `test-quality-review` : **focused**. Revue de conformité, authentification, OPA, reprise et tests, sans modification du code ou des tests. Les deux constats ci-dessous portent sur la **baseline avant correction**.

## Verdict

**Un défaut d'expiration dans B et un défaut dans l'oracle commun sont reproduits.** Aucun contournement supplémentaire d'identité, de périmètre Rego ou de consentement n'a été observé dans le périmètre examiné. La réussite des suites existantes ne couvre pas les deux fenêtres reproduites.

La référence est [l'archive avant revue](../../../experiments/results/before-review/manifest.json), complétée par le [manifest B](../../../experiments/b_broker/evidence/source-manifest.json). Les 19 fichiers de ce dernier correspondaient à leurs SHA-256 au début de la revue : [vérification](../../../experiments/results/review-b/manifest-check.json). Racine documentaire : `docs`, faute de configuration Git locale disponible. Aucun dépôt Git n'a été initialisé.

Sources lues : contrat commun, plan B, note d'implémentation, README B, totalité du broker, superviseur OPA, bootstrap, politiques/tests Rego, tests Python B, fournisseur et ses tests ; helpers/cas pertinents de la campagne commune. Les conclusions ne concernent pas les autres approches.

## High-Risk Behavioral Gaps

### B-R1 — P1 / risque élevé : expiration dépassée pendant la persistance, puis envoi

**Emplacement baseline :** [broker.py:388](../../../experiments/b_broker/broker.py#L388), contrôle temporel avant la transaction ; [broker.py:392](../../../experiments/b_broker/broker.py#L392), transaction d'intention ; [broker.py:400](../../../experiments/b_broker/broker.py#L400), reprise puis IO sans nouveau contrôle.

`execute()` évalue Rego et l'expiration avant `BEGIN IMMEDIATE`. L'attente du verrou SQLite et le commit peuvent dépasser la durée encore autorisée. Le code effectue ensuite l'appel fournisseur sans vérifier de nouveau l'heure. Le contrat exige la validité au moment d'exécuter ; la note B annonce un contrôle frais avant chaque lecture/envoi protégé.

**Reproduction principale, sans hook ni modification de source :** créer un grant expirant dans trois secondes, soumettre un email et obtenir `pending`, détenir `BEGIN IMMEDIATE` sur sa base jetable depuis une connexion de test, puis lancer l'approbation HTTP. Relâcher le verrou après expiration. L'approbation, bloquée sur son intention durable, continue alors jusqu'au fournisseur. Résultat enregistré : expiration `1789929002`, libération à `1789929002.1566458`, aucun effet avant libération, puis HTTP 200 / `executed` et **un email enregistré après expiration**. Le verrou est une injection de délai de stockage ; cette reproduction ne prétend pas qu'un agent HTTP possède l'accès à SQLite.

**Confirmation complémentaire :** avec le hook existant `after_intent`, suspendre puis reprendre le processus après expiration produit aussi un ordre exécuté ; aucun effet n'existe avant reprise. Le délai est situé après contrôle et avant l'appel fournisseur, pas dans un appel déjà en vol.

**Action :** recontrôler le temps applicable au grant/snapshot/consentement après le commit, immédiatement avant tout IO protégé ; enregistrer un résultat terminal sans envoi quand il est expiré. Ajouter un test qui laisse passer une échéance pendant la persistance ou la pause avant envoi, puis vérifie zéro effet/lecture supplémentaire et aucun envoi lors du replay. Un dernier contrôle local ne garantit toujours pas l'heure d'acceptation par un fournisseur distant : conserver explicitement cette limite.

**Preuves :** [reproduce.py](../../../experiments/results/review-b/reproduce.py), cas `expiry_during_intent_lock` et `expiry_after_intent`, [résultats JSON](../../../experiments/results/review-b/reproduction.json), [journal](../../../experiments/results/review-b/reproduction.log). Les effets et snapshots complets y sont conservés.

### B-R2 — P2 / risque moyen : une commande fournisseur rejetée modifie son prochain comportement

**Emplacement baseline :** [provider.py:114](../../../experiments/common/provider.py#L114), `UPDATE control` avant validation du document ; [provider.py:118](../../../experiments/common/provider.py#L118), retour 400 dans le contexte transactionnel.

`POST /control` modifie d'abord `mode`, puis valide `document`. Un document invalide renvoie HTTP 400 par un `return` normal, donc le contexte SQLite valide malgré tout le changement de mode. Cela affaiblit l'oracle : une configuration annoncée rejetée influence l'effet suivant et peut contaminer un scénario de panne.

**Reproduction :** envoyer `{"mode":"reject_before","document":{"id":"not-public-note","version":2,"content":"invalid"}}`. Réponse observée : **400 `invalid_document`**. Envoyer ensuite un effet valide, alors que le mode initial était normal : réponse **503 `synthetic_provider_rejection`**, avec zéro effet. La commande rejetée a donc installé la panne.

**Action :** valider l'ensemble de la commande avant toute mutation, ou assurer un rollback lors du rejet. Ajouter une régression qui vérifie le mode et le document inchangés après une commande invalide ; le prochain effet normal doit être créé. C'est un défaut du dispositif de test, accessible avec le seul credential fournisseur/root ; aucune escalade de privilèges d'un agent n'est revendiquée.

**Preuves :** cas `rejected_control_mutates_mode` du même [script](../../../experiments/results/review-b/reproduce.py) et des mêmes [résultats](../../../experiments/results/review-b/reproduction.json). SHA-256 baseline du fournisseur : `78c020888ffdc43119ef37c93bbc819901a3dd455804f3c4cdac585211447768`.

## Weak or Misleading Tests

Aucun constat supplémentaire. Les tests locaux sollicitent les vrais processus, HTTP, Rego et SQLite. Les assertions de panne OPA portent sur des états refusés et l'absence d'effet ; la concurrence vérifie à la fois l'effet observable et l'unicité durable. Les contrôles `/proc`/permissions testent la configuration de déploiement annoncée et ne sont pas présentés comme une preuve d'isolation contre le même utilisateur OS.

La limitation concrète est temporelle : `test_crash_intent_recovery_without_redispatch` tue le processus aux points d'arrêt et vérifie la reprise, mais ne le laisse pas reprendre vivant après expiration. Le test commun d'expiration laisse expirer **avant** l'approbation. Ces scénarios passent sans couvrir B-R1. De même, les quatre tests fournisseur ne soumettent aucune commande `/control` invalide, d'où B-R2. Ces lacunes sont intégrées aux deux constats, sans les compter deux fois.

## Regression Coverage Findings

Les régressions nécessaires sont celles de B-R1 et B-R2 : observer les effets/lectures et le replay, pas seulement un statut HTTP ou un compteur SQL. Les tests Rego natifs protègent les règles et les bornes d'âge au moment de l'évaluation ; ils ne peuvent pas protéger à eux seuls le délai entre la décision et l'effet externe.

## Mocking and Fixture Friction

Préoccupation faible concernant les mocks : aucune substitution de moteur dans les preuves examinées. Les politiques invalides, indéfinies, conflictuelles et mal formées sont de vrais fichiers Rego exécutés par OPA. Les hooks de pause sont configurés au lancement par le test, hors interface agent. La majorité de la complexité des fixtures correspond à une intégration réelle ; les helpers communs rendent nécessaire la revue séparée du fournisseur, effectuée ici.

## Validation et commandes

Exécutions de cette revue, dépendances déjà présentes, sockets Unix/loopback autorisés après constat du blocage de sandbox :

```sh
experiments/b_broker/.tools/opa-1.9.0/opa check --strict experiments/b_broker/policy
experiments/b_broker/.tools/opa-1.9.0/opa test experiments/b_broker/policy -v
```

**12/12 Rego**, strict check réussi : [journal](../../../experiments/results/review-b/rego-tests.log).

Depuis `experiments/b_broker` :

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests --basetemp=../results/review-b/pytest-tmp
```

**13/13 Python**, 18,71 s : [journal](../../../experiments/results/review-b/python-tests.log).

Depuis la racine du projet :

```sh
PYTHONDONTWRITEBYTECODE=1 experiments/b_broker/.venv/bin/python -m unittest -v experiments/common/test_provider.py
PYTHONDONTWRITEBYTECODE=1 experiments/b_broker/.venv/bin/python experiments/results/review-b/reproduce.py
```

**4/4 tests fournisseur**, 2,047 s : [journal](../../../experiments/results/review-b/provider-tests.log). **3 reproductions positives** : deux variantes de B-R1, une de B-R2. Le script affirme le comportement défectueux de la baseline ; il doit échouer après correction, ce n'est pas un test d'acceptation de la correction.

La campagne indépendante du coordinateur, exécutée séparément avant cette revue, indique **30/30 pour B**, 16 effets et 14 lectures : [rapport root](../../../experiments/results/root-before-review/report.json). Ce résultat a été lu, pas recompté comme une nouvelle exécution de cette revue. Aucun résultat de performance comparatif n'est déduit de ces durées.

## Limites admises, distinctes des défauts

- `unknown` terminal après perte de réponse ou interruption, sans reprise aveugle : compromis de disponibilité explicitement admis. Une intention sans effet peut rester inconnue ; aucune promesse d'exécution exactement une fois hors fournisseur synthétique.
- Sérialisation globale, un seul processus par état, révocation derrière un appel déjà en cours, délai cumulé des préparations : limites documentées. B-R1 concerne une expiration avant un appel qui n'a pas encore commencé.
- Même utilisateur OS, tokens de fixture, transport loopback, prix demandés synthétiques, plafonds par opération et absence de budget agrégé : exclusions explicites, pas des bugs ajoutés à la liste.
- La revue ne certifie pas le déploiement, une identité OAuth réelle, un système distribué ou toutes les pannes de stockage. Les scénarios non exécutés ne sont pas présentés comme validés.

## Design Signals Revealed by Tests

1. **OPA est réutilisable comme frontière de décision, pas comme cycle d'exécution.** Les tests natifs et les refus de résultats invalides démontrent l'apport du moteur réel. Le défaut temporel apparaît dans l'enchaînement local persistance/envoi, responsabilité qui reste au broker même avec une politique correcte.
2. **Le protocole HTTP centralise effectivement des responsabilités partagées.** Email, commande et lecture réutilisent grant, snapshot, consentement, intention et replay. Pour réutiliser ce broker, il faut porter explicitement les contrats de snapshot et de fournisseur ; une nouvelle règle Rego ne dispense pas d'un adaptateur de préparation/exécution correct.
3. **Les effets observables rendent les compromis et défauts visibles.** Les tests de crash établissent une reprise conservatrice, tandis que le fournisseur indépendant permet de distinguer décision, intention et effet. La correction B-R2 rappelle que cet oracle constitue lui-même du logiciel critique pour les conclusions de l'expérience.

## Recommended Actions

Corriger B-R1 dans B et B-R2 dans le fournisseur commun sous leurs propriétaires respectifs, conserver cette revue comme preuve pré-correction, puis exécuter les deux régressions comportementales et les suites affectées. Aucun autre changement d'architecture n'est nécessaire pour traiter les défauts reproduits.
