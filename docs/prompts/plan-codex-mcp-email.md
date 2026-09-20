# Mission : planifier un premier usage de Moraine depuis Codex

**Mission historique exécutée.** Le plan, le pilote et le laboratoire local
existent désormais. Consulter l’[état courant](../status.md) avant toute reprise;
les restrictions et hypothèses ci-dessous décrivent la phase initiale.

Tu travailles dans `/home/alacasse/projects/moraine`. Produis en français un plan de réalisation qui permette de passer des prototypes existants à un premier usage utile depuis Codex.

**Mandat : planification uniquement.** Tu peux lire le code, les preuves et la documentation publique. Écris le plan dans `docs/plans/codex-mcp-email-pilot.md`. L'implémentation, l'installation dans Codex, la configuration de comptes, l'utilisation de secrets, les appels API payants, les envois réels et la publication appartiennent à une étape ultérieure. Conserve les prototypes, leurs tests et leurs preuves. Respecte les instructions applicables et vérifie l'état du workspace avant de proposer des opérations Git; aucun dépôt Git utilisable n'était présent pendant l'expérience.

## Direction de départ

L'utilisateur cherche une brique open source sous Linux qui contrôle les accès et les actions d'un agent indépendamment de son raisonnement. Il veut maintenant atteindre rapidement un usage concret dans l'environnement OpenAI qu'il connaît, en commençant par Codex.

Le chemin retenu pour ce cadrage est :

**Codex → interface MCP → service B → adaptateur email → boîte dédiée.**

Un canal humain distinct permet de créer/révoquer la délégation et d'approuver une action précise. Le modèle peut proposer une action et consulter son état; il ne reçoit pas les pouvoirs d'approbation humaine ou les identifiants du fournisseur.

Pars de B comme base de travail. Une modification de cette direction doit répondre à une difficulté concrète, démontrée dans le code ou dans une contrainte d'intégration. La première adaptation métier proposée est l'email; le fournisseur, le mécanisme de sélection des messages et le détail du déploiement restent à choisir. Les futurs adaptateurs servent à évaluer la réutilisabilité de l'interface, sans les inclure dans le premier développement.

## Contexte à reprendre, sans recommencer l'enquête

Trois plans distincts ont été implémentés et comparés :

- **A :** module Python embarqué, apparitor 0.1.1 et Cedarpy 4.8.7.
- **B :** broker HTTP indépendant, OPA 1.9.0/Rego et état SQLite.
- **C :** droits Biscuit signés et atténuables, avec révocation et approbations conservées côté serveur.

Les moteurs sont réels. Les identités, les documents et les fournisseurs email/commande sont synthétiques. Après revue et correction, la campagne enregistrée donne 30 scénarios communs réussis par approche et 115 tests locaux au total. Ces résultats concernent ce périmètre; ils ne prouvent ni l'isolation OS, ni l'intégration d'un vrai fournisseur, ni la demande d'utilisateurs externes.

La revue a notamment trouvé des expirations franchies pendant une écriture SQLite ou entre deux lectures de pièces jointes, ainsi que des défauts d'assertion dans le banc commun. Les corrections et les preuves avant/après ont été conservées. La revue A a été interrompue par un filtre automatique puis complétée par le coordinateur; cette provenance est documentée.

Lis dans cet ordre :

1. `docs/experiments/COMPARISON.md` et `docs/experiments/EXPERIMENT.md` : conclusions, contrat et limites.
2. `docs/experiments/B-implementation.md` et `docs/experiments/b-broker.md` : comportement actuel et corrections. Les sections antérieures à la revue décrivent une baseline historique.
3. `experiments/results/final-summary.json`, `experiments/results/final-campaign/report.json`, `docs/experiments/reviews/B-review.md` et les preuves ciblées qu'ils référencent. Distingue défaut initial et statut après correction; vérifie les sources si une conclusion dépend de leur version.
4. Le code utile dans `experiments/b_broker/`, en particulier `broker.py`, `opa.py`, `policy/`, les scripts de démarrage et les tests. Identifie ce qui est réutilisable et ce qui est lié à la fixture : Alice/Bob, jetons de lancement, schémas, données et contrat du fournisseur.

Consulte `docs/research/delegated-authority-investigation.md` si une décision nécessite le contexte de l'écosystème. La conclusion initiale reste pertinente : l'utilité d'une nouvelle bibliothèque générique n'est pas établie; une intégration ciblée ou une contribution à l'existant peut suffire. A et C sont des références comparatives à consulter sur une question précise.

## Travail demandé

### 1. Définir une première expérience utilisateur complète

Décris un parcours concret : sélectionner quelques messages/documents, demander une réponse depuis Codex, voir le contenu exact soumis à approbation, approuver ou refuser, puis connaître le résultat de l'envoi.

Sépare une démonstration avec fournisseur simulé d'un usage avec une vraie boîte dédiée. Pour chaque étape, précise ce que l'agent peut lire, ce qu'il peut demander, ce que l'humain décide et ce qui est effectivement exécuté. Donne un critère observable de réussite pour le premier usage.

### 2. Déterminer l'intégration minimale avec Codex

Vérifie les capacités actuelles dans la documentation officielle OpenAI, en suivant le skill `openai-docs` s'il est disponible. Point d'entrée : https://learn.chatgpt.com/docs/extend/mcp?surface=cli . La documentation et le cadrage ne nécessitent pas de clé API. Aucune modification de la configuration Codex n'est demandée pendant cette mission.

Propose les quelques outils MCP nécessaires, avec leurs entrées, sorties et états utilisateur. Choisis un transport justifié. Distingue l'interface MCP côté agent des adaptateurs côté fournisseurs. Le service doit pouvoir retourner une demande en attente et permettre sa consultation ultérieure, sans garder un appel d'outil ouvert pendant toute la revue humaine.

Précise comment les actions MCP correspondent aux opérations du broker et quelles modifications sont nécessaires. Une interface MCP ne contrôle pas automatiquement les autres outils natifs ou connecteurs disponibles dans Codex.

### 3. Définir la séparation des pouvoirs pour le pilote

Dessine une architecture simple indiquant les processus, identités Linux, fichiers d'état, secrets et chemins réseau. Justifie ce qui empêche l'agent d'accéder au fournisseur ou d'approuver lui-même une action, en tenant compte de ses outils shell, fichiers et navigateur.

Le prototype tourne sous un même utilisateur OS; démarrer un processus supplémentaire ne suffit donc pas à établir cette séparation. Compare seulement les options nécessaires au pilote et recommande la plus simple qui assure la propriété annoncée.

Décris l'authentification humaine, l'affichage du contenu exact et la liaison entre l'approbation et la demande. Une affirmation `approved=true` du modèle ou une confirmation générique du client n'est pas, à elle seule, cette preuve. Les routes de gestion humaine ne doivent pas devenir des outils agent privilégiés. Explicite aussi les droits limités des identifiants réellement accessibles à Codex.

### 4. Choisir le premier adaptateur email

Compare au maximum deux options plausibles de fournisseur/connexion, puis recommande un défaut argumenté. Distingue les informations indispensables de l'utilisateur des hypothèses permettant de continuer le plan. Appuie les capacités du fournisseur sur ses sources officielles.

Définis le contrat de l'adaptateur : sélection du contexte, lecture autorisée, préparation/normalisation des destinataires et pièces jointes, snapshot approuvé, exécution et interprétation du résultat. Précise le périmètre du premier envoi : réponse, destinataires, format et pièces jointes réellement pris en charge.

Vérifie particulièrement les garanties du vrai fournisseur sur l'idempotence, les erreurs et la perte de réponse. Le fournisseur simulé possède une déduplication et des rejets explicites qui ne se transfèrent pas automatiquement à une API email ou à SMTP. Préserve un résultat `unknown` et une conduite utilisateur claire lorsqu'on ne sait pas si l'envoi a eu lieu.

### 5. Construire les étapes de réalisation et leur validation

Découpe en étapes donnant chacune un résultat démontrable. Pour chaque étape : objectif, modules/fichiers concernés, réutilisation ou extraction depuis B, dépendances, tests d'acceptation, preuve attendue et éventuelle action humaine nécessaire. Préserve les preuves expérimentales existantes; propose un emplacement distinct pour le pilote et les nouveaux résultats.

La validation doit couvrir le parcours réel depuis Codex, les limites de lecture, le contenu approuvé, la séparation des identités, l'expiration/révocation avant chaque accès pertinent, le replay, la reprise et les résultats incertains. Observe les lectures et effets; le simple refus annoncé par le service ne suffit pas. Prévois une revue distincte de l'auteur des changements sensibles.

Donne un ordre de grandeur argumenté de l'effort et les dépendances pouvant le modifier. Identifie le chemin le plus court vers une utilisation réelle et ce qui doit rester hors du pilote. Les contraintes métier du deuxième adaptateur peuvent servir à challenger l'interface proposée, sans créer maintenant un framework de connecteurs.

## Livrable et critère de fin

Le plan dans `docs/plans/codex-mcp-email-pilot.md` doit contenir :

- une recommandation et le parcours du premier usage;
- un schéma des composants et des pouvoirs;
- le contrat minimal des outils MCP et de l'adaptateur email;
- un tableau « réutilisé / à adapter / à créer », fondé sur le code actuel;
- les étapes ordonnées et leurs critères d'acceptation;
- les limites, hypothèses, décisions utilisateur restantes et sources vérifiées;
- les observations à recueillir pendant le pilote pour décider si cette brique mérite d'être poursuivie.

Le travail est terminé quand un agent de développement peut prendre la première étape sans inventer ses frontières d'autorité, ses dépendances ou ses critères de réussite. Présente ensuite une synthèse courte et **une seule décision utilisateur prioritaire**, avec ta recommandation et son effet sur le plan. Pour les autres incertitudes, propose des hypothèses explicites et identifie ce qui devra être confirmé avant l'étape concernée.
