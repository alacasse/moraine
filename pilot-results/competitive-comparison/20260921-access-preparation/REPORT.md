# Comparaison Arcade / Workato — campagne partielle

Date : **21 septembre 2026**. Résultat : **préparation locale achevée;
aucun essai authentifié chez Arcade, Workato ou Confluence**. Les quatorze
scénarios S0–S6 des deux candidats restent bloqués par des prérequis. La
recherche publique ne permet pas de départager leur couverture effective.

## Mandat, périmètre et état initial

L'utilisateur a demandé de lire et exécuter le
[prompt de reprise](../../../docs/prompts/run-agent-access-comparison.md).
Ce mandat autorise la préparation et les observations réalisables, mais
exige la désignation et l'autorisation des comptes, connexions et dépenses
avant les essais externes. Aucun compte, tenant, IdP, consentement OAuth ou
budget payant n'a été désigné dans cette session à la clôture de ce bilan.
Une demande ciblée sur la source S0 a été présentée pendant le travail local;
aucune autorisation supplémentaire n'est présumée en l'absence de réponse.

Racine documentaire résolue : `docs/` (aucune valeur locale `codex.docs-root`).
Code et documentation appartiennent au même dépôt Moraine. Le HEAD est
`29a883450f585fc6662e151de133559670fc5864`. Les recherches, le plan, le prompt
et la revue existaient localement hors commit, avec une modification préalable
de `docs/README.md`. Leurs bytes sont conservés, ainsi que les autres fichiers
préexistants recensés dans [l'inventaire initial](preexisting-inventory.json).

Le [plan figé](PLAN.md) est identique byte à byte à la capture v2 déjà revue :
`24b480003e61d742b8bb24af7f9ecfa2580e84069f9f6e045a7ac79549eea497`.
La [revue](../20260921-plan-review/REPORT.md) et sa
[contre-revue](../20260921-plan-review/REVIEW-v2.md) ont été lues. Aucun écart
de protocole, aucune nouvelle revue de plan. Le statut ancien « exécution non
autorisée » demeure dans la capture historique; le [mandat courant](MANDATE.md)
autorise la présente préparation, sans autoriser les opérations externes non
précisées. Aucun code Moraine, réglage global, compte ou service n'a été modifié.

## Livrables de préparation

| Livrable | Ce qu'il contient |
| --- | --- |
| [Matrice](matrix.csv) | 21 lignes : sept scénarios par candidat et sept lignes de référence Moraine; verdict, nature de preuve, mode, couche, identités, interventions, temps, appels, blocage et limites |
| [Fiche Arcade](arcade-prerequisites.md) | Éditions, accès, OAuth/OIDC, scopes candidats, identité A/B, révocation, audit, versions et permissions manquantes |
| [Fiche Workato](workato-prerequisites.md) | Free, Identity/VUA, connexion Confluence, scopes prescrits, traces et inconnues A/B |
| [Fiche Confluence](source-prerequisites.md) | Tenant, O/U, édition pour D4, durée/fin d'essai, facturation et périmètre S0 |
| [Corpus fictif](corpus/index.json) | D1 plan Atlas et D2 budget complémentaire; D3 témoin lisible par U seul; D4 réservé à O; marqueurs séparés de titre/corps, IDs synthétiques, empreintes |
| [Mode opératoire](RUNBOOK.md) | Gestes S0–S6, contrôle B vers A, reprise, révocation et nettoyage |
| [Configuration expurgée](configuration.redacted.json) | Valeurs proposées séparées des identifiants et scopes effectifs encore absents |
| [Inventaire des versions](versions.json) | Versions documentées distinctes des versions non observées de déploiement |
| [Cas de collecte](collection/cases.json) | 126 contrôles planifiés, aucun exécuté; horaires et invariants du retrait de A |
| [Manifeste](manifest.json) | Entrées, captures, empreintes des livrables et références historiques |

Les IDs Confluence, versions de pages, identités authentifiées et résultats
restent inconnus. Les modèles de relevé ne sont pas des transcriptions d'essai.
Les fichiers [source](collection/source-observations.json) et
[appels](collection/transcripts.redacted.json) ont des listes vides explicites.
Le [registre](collection/resource-register.json) confirme qu'aucune ressource
externe ni aucun processus serveur n'a été créé; le nettoyage externe est
donc sans objet. Les preuves locales sont conservées.

## Ce qui a réellement été fait chez chaque candidat

| Offre | Travail réalisé | Essais S0–S6 | Limite décisive |
| --- | --- | --- | --- |
| Arcade | Consultation de documentation publique et du schéma officiel des hooks; fiche de préparation | Aucun; bloqués par prérequis | Compte/projet, édition, IdP et OAuth non désignés; contrôle serveur par délégation et par document à qualifier |
| Workato | Consultation de documentation publique, tarifs, Identity/VUA et connecteur; fiche de préparation | Aucun; bloqués par prérequis | Workspace et OAuth non désignés; capacités effectives, scopes et séparation A/B à qualifier |
| Moraine | Lecture du contrat, du rapport et des contrôles historiques; vérification d'intégrité | Aucun nouvel essai | Une seule identité agent, source JSON fictive, accord simulé, captures de 30 minutes |

**Aucun refus d'accès concurrent, fuite, délai de révocation ou geste utilisateur
n'a été observé dans un produit.** Les colonnes d'appels de cette campagne
valent zéro; les mesures historiques non relevées restent vides. Le terme
« documenté seulement » des lignes Moraine signifie preuve historique
consultée et bornée, pas réussite du protocole commun S0–S6.

## Résultats documentaires qui changent la préparation

**Arcade fournit un mécanisme candidat pour S2.** Son architecture décrit des
jetons OAuth limités à une passerelle. Il faut encore démontrer que les droits
sur D1/D2 sont liés côté serveur à la délégation de A ou B. Une passerelle ou
un `client_id` distinct ne suffit pas. Les hooks sont une surface d'extension
documentée, mais la logique doit être fournie par l'intégrateur; elle n'a pas
été développée. [Architecture](https://docs.arcade.dev/en/operate/deploy/architecture),
[contrôles](https://docs.arcade.dev/en/operate/governance/contextual-access).

**Workato documente le chemin fournisseur sous U.** VUA et `User's connection`
conviennent comme piste d'essai; les jetons MCP et le retour d'une recette
imbriquée à un compte de service ne seraient pas équivalents. Le guide du
connecteur prescrit aussi des scopes de gestion/écriture : leur nécessité
effective pour les seuls outils de lecture reste inconnue. Le sous-ensemble
minimal doit être vérifié avant consentement. [VUA](https://docs.workato.com/en/mcp/verified-user-access),
[connecteur](https://docs.workato.com/en/connectors/confluence.html).

**Le prix d'entrée ne prouve pas l'accès au protocole complet.** Les fiches
détaillent les conditions Free, les fonctions d'entreprise, les divergences
commerciales et les valeurs inconnues. Aucun prix affiché n'est traité comme
budget autorisé. [Tarifs Arcade](https://www.arcade.dev/pricing/),
[offre Workato](https://www.workato.com/free).

**La source exige une préparation propre.** D4 nécessite une édition permettant
les restrictions; Free ne convient pas. La durée d'essai diverge entre les
pages officielles (7 jours sur les tarifs, 14 jours pour Standard depuis Free
dans le guide). L'écran effectivement proposé devra fixer échéance et sortie
d'essai avant activation. [Permissions](https://support.atlassian.com/confluence-cloud/docs/what-are-confluence-cloud-permissions-and-restrictions/),
[tarifs](https://www.atlassian.com/en/software/confluence/pricing),
[guide des plans](https://support.atlassian.com/confluence-cloud/docs/learn-about-confluence-cloud-plans/).

Ce sont des contraintes ou ambiguïtés **documentaires**. Les frictions de
configuration, consentements répétés, compréhension, reprise ou révocation
restent non mesurées. L'absence d'accès dans cette session ne prouve ni refus
commercial du fournisseur ni absence de fonction.

## Référence Moraine et possibilités de réutilisation

La [preuve existante](../../codex-email/20260921-agent-access/REPORT.md) conserve
deux conversations Codex lisant le même grant, une récupération de deux objets
fictifs et des refus après révocation par l'opérateur simulé. Son
[contrôle natif](../../codex-email/20260921-agent-access/native-checks.json)
et son [contrôle de retrait](../../codex-email/20260921-agent-access/revocation-checks.json)
ont été lus. Cela illustre persistance de demande, sélection et retrait dans
ce pilote; cela ne couvre pas deux agents, Confluence, OAuth, annuaire ou
consentement indépendant. Les 122 tests du rapport restent un résultat
historique : aucune suite n'a été relancée ici.

Les passerelles, connexions utilisateur, connecteurs et traces documentés
justifient d'essayer la réutilisation de l'une des offres avant de reconstruire
ces composants. Si le contrôle fin exige une extension, il faudra d'abord
identifier le signal A/B authentifié et le point de contrôle, puis estimer
conception, implémentation et vérification séparément. L'effort est **non
estimable de façon défendable à ce stade**; aucune extension n'est déclarée
nécessaire ou « petite » sur la seule base de ces lectures.

Les différences possibles pour Moraine restent des hypothèses : délégations
par agent compréhensibles, portée par ressource, demande d'extension durable et
retrait sélectif explicable. Ni leur absence chez Arcade/Workato ni une
supériorité de Moraine n'ont été démontrées. Particuliers et entreprises restent
des publics possibles. Cette campagne ne mesure aucune volonté de payer et
ne choisit aucun marché.

## Effort et première décision restante

Les recherches déléguées ont relevé 3 min 02 s écoulées pour Arcade et
2 min 17 s pour Workato, lecture/rédaction comprises, en parallèle. Ces durées
ne sont pas des temps de mise en service. Le travail partagé (corpus,
Confluence, matrice et validation) est consigné dans [timing.json](timing.json)
comme fenêtre écoulée, sans répartition active artificielle. Configuration
externe et scénarios : zéro. Attente d'accès : aucune session fournisseur
ouverte. Les plafonds de trois heures de préparation active puis deux heures
de scénarios par offre n'ont pas été atteints; l'autorisation et les accès
manquent avant toute exécution.

**Première décision : désigner la source pour S0.** L'intervention exacte est
décrite dans la [fiche Confluence](source-prerequisites.md) : tenant fictif
autorisé, O administrateur et U ordinaire distinct, trois espaces et quatre
pages, contrôle direct puis retrait des ressources créées. À défaut de site
existant, préciser les identités et autoriser sa création sans carte ni dépense.
Cette décision n'emporte pas autorisation OAuth Arcade/Workato. Les fiches des
offres permettent ensuite de préparer leur périmètre exact, une décision à
la fois. Les deux candidats sont conservés.

## Vérifications et livraison

Les contrôles exécutés sont consignés dans [validation.json](validation.json) :
empreintes du plan et des fichiers antérieurs, preuves historiques contre leur
manifeste et archive, liens locaux, structure JSON/CSV, droits et marqueurs du
corpus, cohérence des cas, recherche de motifs de secrets et espaces finaux.
Un aperçu de la matrice a été inspecté; seul le CSV demandé est livré.
`git diff --check` est complété par le contrôle direct des nouveaux fichiers,
car ils ne sont pas suivis. Ces vérifications portent sur la préparation,
**pas sur les contrôles d'autorisation des fournisseurs**.

Aucun compte, OAuth/SSO, installation système, appel produit/modèle externe,
contact commercial, envoi réel, commit ou push n'a été réalisé. La prochaine
campagne externe devra utiliser un nouveau dossier et conserver celle-ci.
