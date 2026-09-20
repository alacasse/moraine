# Trois approches de l'autorité déléguée : résultats et apprentissages

Campagne locale du 20 septembre 2026. Trois plans indépendants ont été transmis à trois développeurs distincts, puis revus sur une baseline archivée. Le coordinateur possède le contrat, le fournisseur synthétique et la campagne commune. Aucun compte réel, message, paiement, commit ou déploiement externe.

Cette comparaison conserve la recommandation issue de cette campagne : A pour
une intégration embarquée, B pour un service. Le [pilote email ultérieur](../plans/codex-mcp-email-pilot.md)
a retenu B pour son service MCP; cela ne constitue pas une validation produit de
A ou de B auprès de développeurs extérieurs. Voir l'[état courant](../status.md).

## Ce que l'expérience change dans notre décision

**Les trois directions sont réalisables avec de vraies briques open source. Le travail difficile restant est le cycle d'exécution : préparer ce qui sera approuvé, conserver cette décision, vérifier qu'elle est encore valable, puis rendre compte honnêtement de l'effet obtenu.** Un moteur de règles ou un jeton signé ne prend pas en charge ce cycle à notre place.

Pour le prochain essai auprès de développeurs Python, **A est ma base privilégiée**, car son interface regroupe ce cycle dans le backend qui possède déjà l'outil. Cette préférence reste une hypothèse d'intégration; nous n'avons pas encore mesuré le travail d'un développeur extérieur. **B est le candidat pertinent si les premiers utilisateurs veulent un service commun à plusieurs applications ou langages.** C devient intéressant lorsqu'un besoin réel de restrictions transportables et d'atténuation sans retour à l'émetteur est établi.

La prochaine question produit est concrète : un développeur souhaite-t-il déléguer à cette brique la préparation, l'approbation et la reprise de son outil, et quel travail lui reste-t-il pour son fournisseur? Ces expériences apportent du code pour poser cette question. Elles n'établissent pas encore qu'un nouveau projet générique manque à l'écosystème.

## Comparaison des implémentations

| | A — module Python embarqué | B — service d'exécution OPA | C — capacités Biscuit |
|---|---|---|---|
| Réutilisation exécutée | apparitor 0.1.1 + Cedarpy 4.8.7 | OPA 1.9.0 / Rego + HTTPX | biscuit-python 0.4.0 + HTTPX |
| Interface à intégrer | `ExecutionGate` dans un backend fiable; HTTP sert de démonstrateur | HTTP de soumission, consultation et approbation | HTTP + jeton dans chaque soumission; client d'atténuation indépendant |
| Origine des droits | Identité du backend et grant conservé côté serveur; Cedar évalue | Identité du broker et grant serveur; Rego évalue | Identité authentifiée + droits signés et restrictions ajoutées; révocation serveur |
| Apport distinct | Contrôle réel des résultats Cedar, orchestration apparitor, interface embarquée | Politiques dans un processus OPA séparé, API indépendante du langage client | Chaîne signée et restrictions ajoutées avec la seule clé publique |
| État encore nécessaire | Grants, snapshots, demandes, résultats et replay SQLite | Même cycle, avec consentements et intentions explicites; supervision OPA | Même cycle, avec clé émettrice, jetons et correspondance de révocation |
| Coût d'intégration observé | Hôte responsable de l'authentification et de l'absence d'accès fournisseur contournant le module | Processus et socket OPA, politiques, secret fournisseur, état et supervision | Python 3.13 local pour le binding, clés, scopes Datalog, état de révocation et bornes d'évaluation |
| Limite structurante | Le code dans le backend fiable peut contourner le module | Un processus propriétaire et un verrou global; frontière OS non démontrée | L'atténuation garde l'acteur Alice; elle ne transfère pas son identité et ne révoque pas le parent |

Les bibliothèques de politiques sont réelles : aucune simulation de Cedar, OPA ou de signature Biscuit ne remplace leur comportement. En revanche, les fournisseurs email/commande et les identités sont des fixtures. Les versions sont celles effectivement exécutées et verrouillées pour cette campagne, sans prétention qu'elles soient les plus récentes.

Les trois prototypes ont volontairement des implémentations séparées. Les réunir immédiatement dans une grande abstraction ferait perdre une partie de l'apprentissage. Les documents détaillent les responsabilités héritées et celles écrites pour l'expérience : [A](A-implementation.md), [B](B-implementation.md), [C](C-implementation.md).

## Résultats vérifiés

La campagne indépendante avant revue a donné **30/30 pour chaque approche** : [rapport avant revue](../../experiments/results/root-before-review/report.json). Elle observe le fournisseur séparément des réponses d'autorisation : nombre d'effets, contenu effectivement envoyé, accès aux documents, répétitions et reprises.

**Après correction, la campagne finale indépendante passe à nouveau à 90/90 : 30/30 pour A, B et C**, cette fois avec les assertions renforcées. Chaque approche produit les 16 effets et 14 lectures attendus sur cette campagne : [rapport final et hashes des sources](../../experiments/results/final-campaign/report.json).

| Suite finale | Résultat | Preuve |
|---|---|---|
| A, dont 3 nouvelles régressions temporelles | 40 tests Python réussis | [Journal du coordinateur](../../experiments/results/root-a-regression-after.log) |
| B, dont 4 nouvelles régressions temporelles | 17 tests Python + 12 tests Rego réussis | [Journal complet](../../experiments/b_broker/evidence/post-review-local-tests.log) |
| C, dont 6 nouvelles régressions | 41 tests Python réussis | [Résumé et preuves](../../experiments/c_capability/evidence/post-review-summary.json) |
| Fournisseur commun, dont refus atomique d'une commande invalide | 5 tests réussis | [Journal indépendant final](../../experiments/results/final-local-checks/provider.log) |

Cela représente **115 tests locaux, plus 90 scénarios communs**. Les suites B/C complètes ont été exécutées par leurs développeurs après correction; le coordinateur a également relancé les régressions ciblées B/C et les tests fournisseur : [commandes et résultats indépendants](../../experiments/results/final-local-checks/results.json). Le consentement B a été laissé expirer pendant ses 60 secondes réelles, ce qui explique une partie de la durée de sa suite.

Un scénario commun inclut 64 demandes générées autour des bornes de commande; elles ne sont pas comptées comme 64 scénarios supplémentaires. Les temps figurent dans les preuves pour reproduction, mais incluent démarrages, arrêts et attentes intentionnelles. Ils ne constituent pas un classement de performance.

Les scénarios couvrent notamment : absence d'authentification, propriétaire du grant, destinataires To/Cc/Bcc, documents interdits avant accès, corps et pièces jointes exacts, faux consentement, remplacement du contenu, révocation/expiration en attente, concurrence, replay, redémarrage, rejet fournisseur, acceptation suivie d'une perte de réponse. Les suites propres aux approches vérifient le moteur réel et leurs comportements distinctifs.

## Ce que la revue a trouvé malgré les tests verts

| Constat sur la baseline | Approches concernées | Correction et preuve |
|---|---|---|
| Une attente SQLite entre le contrôle d'expiration et l'envoi laisse passer l'échéance | A, B, C | Nouveau contrôle après réservation durable, avant IO; régressions avec verrou réel et absence d'effet/replay |
| Une première pièce jointe lente permet la lecture de la suivante après expiration | A, C | Vérification avant chaque lecture; une seule lecture observée après correction |
| Un surrogate Unicode isolé accepté en entrée ferme la connexion pendant l'encodage | C | Validation UTF-8; réponse 400 et aucun accès fournisseur |
| Une commande `/control` invalide change malgré tout le mode de panne du fournisseur | Instrumentation commune | Validation complète avant mutation; état/document inchangés vérifiés |
| Le test d'autorité de création utilise un corps invalide, donc peut réussir sur le seul refus de schéma | Campagne commune | Grant valide envoyé sous identité agent; 401/403 sans grant retourné exigé |
| Un HTTP 502 peut masquer un faux `state=executed` dans les tests de panne | Campagne commune | Assertion explicite sur l'état, en plus des effets; variante défectueuse désormais détectée |

Les preuves avant correction sont conservées. [Revue A et assertions](reviews/A-review.md), [revue B et oracle](reviews/B-review.md), [revue C](reviews/C-review.md). Les rapports B/C décrivent volontairement leur baseline; les résultats après correction sont distincts.

Le reviewer A a été interrompu par un filtre automatique après avoir enregistré ses vérifications et ses preuves d'assertions. Le coordinateur a complété la revue de A et ses corrections; le rapport détaille cette provenance. Aucun constat issu d'une revue interrompue n'est présenté comme une vérification achevée sans preuve.

Tous les constats du tableau ont été corrigés et les vérifications associées passent. Pour A, les trois nouvelles instances de test échouaient avant correction et la suite passe ensuite à 40 tests : [avant](../../experiments/results/root-a-regression-before.log), [après](../../experiments/results/root-a-regression-after.log). Pour B, les quatre régressions couvrent les délais de grant, de revue, de lecture et de consentement : [journal](../../experiments/b_broker/evidence/post-review-regressions.log). Pour C, six régressions échouaient puis passent, et les sondes inchangées du reviewer confirment les corrections : [résumé](../../experiments/c_capability/evidence/post-review-summary.json). Les [variantes de l'oracle après correction](../../experiments/results/review-a-oracles-after/oracle-probes.json) sont des serveurs volontairement défectueux : leurs échecs aux nouvelles assertions sont le résultat attendu.

## Enseignements techniques et produit

**La bonne unité d'approbation est une action préparée et persistée.** Le système doit conserver le destinataire, le corps, les octets des pièces jointes, l'acteur et le grant pertinents. Une approbation sur une intention vague suivie d'une reconstruction ne fournit pas la propriété testée ici.

**L'autorisation a une durée de validité.** Les règles peuvent être justes au moment de l'évaluation et l'accès suivant arriver trop tard. Les défauts communs de persistance et de préparation montrent pourquoi les points d'appel au fournisseur doivent faire partie du contrat, au-delà de `allow/deny/review`. Un dernier contrôle local réduit ces fenêtres; il ne garantit pas l'heure d'acceptation d'un appel distant déjà émis.

**Un résultat inconnu est un résultat utile.** Dans les trois approches, une acceptation dont la réponse se perd ne devient pas un échec certain. L'intention durable et l'absence de renvoi aveugle protègent des doublons au prix d'une intervention nécessaire. Le fournisseur synthétique possède sa propre idempotence; cela ne prouve pas une exécution exactement une fois chez un fournisseur quelconque.

**Biscuit apporte une capacité spécifique, pas une suppression du serveur.** Les tests montrent l'atténuation dans un processus client sans clé privée, les restrictions qui résistent aux faits ajoutés et la différence entre validité cryptographique hors ligne et révocation en ligne. Le parent reste utilisable par son détenteur et l'approbation humaine ne se transforme pas en signature magique.

**Une contribution ciblée à l'existant mérite d'être examinée.** A reproduit un vrai résultat Cedar `Allow` accompagné d'une erreur d'évaluation; son adaptateur strict le refuse via apparitor. Une option explicite de traitement strict des diagnostics est une piste concrète à discuter en amont. Le cycle durable construit ici n'est pas automatiquement un manque du projet existant : son périmètre peut être différent.

**Le parallélisme a accéléré la comparaison et révélé des erreurs partagées.** Trois équipes ont produit des chemins crédibles, mais plusieurs ont laissé la même fenêtre temporelle. La revue séparée, les délais injectés et l'observation des effets ont fourni plus d'information que les premiers compteurs verts. Le coût supplémentaire doit acheter des contre-exemples et des essais d'intégration, pas seulement trois fois plus de code.

## Prochain essai proposé

Conserver A comme candidat de module et B comme candidat de service, puis faire intégrer le même petit outil de test par un développeur extérieur à sa propre application. Mesurer : temps jusqu'à la première action approuvée, code d'adaptation demandé, erreurs de configuration, compréhension de `unknown`, et préférence pour un module ou un service. Partir d'un compte de test dédié et de contexte sélectionné conserve le besoin email à l'origine du projet. Cet essai réel constitue une étape ultérieure, non exécutée ici.

L'absence de préférence ou de gain observable serait une raison de garder des exemples d'intégration ou de contribuer à une brique existante. Une difficulté récurrente sur les snapshots, l'approbation ou la reprise donnerait au contraire un périmètre plus défendable à une petite bibliothèque.

## Limites et reproduction

Tout tourne sous le même utilisateur Linux, avec jetons et données synthétiques. La séparation HTTP des identités est testée; l'isolation contre du code arbitraire capable de lire les fichiers, arguments ou secrets de cet utilisateur ne l'est pas. Il n'y a pas de production OAuth, de budget de dépenses cumulé, de prix marchand authentifié, de système distribué, de charge soutenue ou de validation par utilisateurs externes. Le test de contenu malveillant prouve que ce texte ne modifie pas l'autorisation technique; il ne mesure pas le taux de prompt injection d'un modèle.

Les [instructions reproductibles](running.md) lancent les trois implémentations et le fournisseur local. [Contrat fixé avant résultats](EXPERIMENT.md), [plans](README.md), [archive avant revue](../../experiments/results/before-review/manifest.json), [manifest final](../../experiments/results/final-source/manifest.json). Aucun dépôt Git utilisable n'était présent : les archives et hashes identifient les sources sans constituer une attestation externe.
