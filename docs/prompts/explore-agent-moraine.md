# Reprise : les agents qui communiquent avec Moraine

Prompt préparé le **21 septembre 2026** pour une prochaine session
d'exploration. À utiliser dans le dépôt `/home/alacasse/projects/moraine`.

## Intention de la session

Je veux continuer à imaginer Moraine avec toi, en français, en explorant cette
fois **le côté des agents qui communiquent avec Moraine** : leur connexion,
leur identité, ce qu'ils peuvent découvrir et demander, puis leur comportement
pendant et après une autorisation humaine.

Relie cette discussion à notre exploration de l'expérience utilisateur et de
la gestion des accès. Nous cherchons à comprendre les possibilités et leurs
conséquences. Je ne veux pas encore choisir entre briques open source,
application complète ou service hébergé, ni trancher notre public principal.

Le mandat est une discussion appuyée sur la lecture des documents et, si
nécessaire, du code ou de sources officielles. Il ne comprend pas de
développement, installation, connexion à un compte réel, campagne de tests,
commit ou push. Préserve les changements déjà présents dans le workspace.

## Contexte à charger

Après les consignes applicables et l'[index documentaire](../README.md), lis :

1. La [note d'exploration](../research/delegation-ux-multi-provider.md),
   notamment ses huit questions **Q1 à Q8**, toutes encore ouvertes. Elle
   conserve les nuances et les attentes exprimées dans la session précédente.
2. L'[état courant](../status.md) pour distinguer ce qui existe, les résultats
   enregistrés et ce qui reste à qualifier.
3. L'[architecture](../architecture.md) et le
   [contrat du pilote](../pilot/interface.md) pour comprendre les pouvoirs
   actuels de l'agent et du canal humain.

Si nous abordons la divulgation avant autorisation ou la publication du
contexte, consulte le [contrat d'ingestion proposé](../plans/email-ingestion-contract.md).
Si nous abordons le contournement par les outils de l'agent, consulte le
[déploiement Linux](../pilot/linux-deployment.md) et ses limites de validation.
Les anciens prompts de planification et d'intégration sont des mandats
historiques, pas le mandat de cette session.

## Ce que nous explorons déjà

- L'utilisateur devrait pouvoir déléguer simplement, sans administrer une
  liste d'éléments autorisés dans une base. Le stockage peut être automatique.
- L'ambition pourrait couvrir les grands fournisseurs email et, plus tard,
  d'autres ressources. Gmail n'est qu'un exemple; la liste et l'ordre des
  intégrations ne sont pas décidés.
- Une piste consiste à demander à l'agent de préparer une configuration.
  Moraine présente les effets précis, obtient une décision humaine indépendante
  et applique les changements autorisés.
- Une application sur téléphone pourrait notifier l'utilisateur, afficher les
  détails et recueillir son acceptation ou son refus. Une interface mobile ou
  web pourrait aussi montrer les accès actifs et permettre de les retirer.
- Nous explorons les rappels et la suspension des accès inutilisés, inspirés
  des applications inutilisées sur Android. La définition de l'inactivité,
  les délais et les règles de reprise restent ouverts.
- Je suis sceptique envers une durée obligatoire à choisir lors de l'octroi.
  La piste actuelle est un accès continu, révocable, avec durée temporaire
  facultative. L'expiration technique d'une demande d'approbation est distincte
  de la durée de l'accès accordé.

Ces pistes ne constituent pas une architecture acceptée. Le pilote actuel
expose quatre outils MCP : `list_context`, `read_context`, `propose_reply` et
`get_request`. Il réserve création/révocation des délégations et décisions au
canal humain. La proposition de configuration par l'agent et l'application
mobile n'y sont pas implémentées. Vérifie ce constat dans les documents actuels
si le dépôt a évolué depuis la rédaction du prompt. Les bornes du pilote ne
définissent pas automatiquement le futur produit.

## Angles à explorer côté agents

Utilise ces angles comme repères dans la conversation, sans chercher à tous
les résoudre dans une première réponse :

| Angle | Questions concrètes et liens avec l'exploration |
| --- | --- |
| Identité et rattachement | Qui appelle réellement : modèle, application qui exécute ses outils, instance, tâche ou sous-agent ? Comment l'utilisateur reconnaît-il cet acteur et l'associe-t-il à son compte Moraine ? Comment éviter de transmettre implicitement ses droits à un autre agent ? **Q1, Q7** |
| Première connexion et découverte | Que faut-il configurer pour un client existant ou une application développée sur mesure ? Que peut découvrir l'agent avant tout accès, y compris noms de comptes/dossiers et métadonnées ? Comment demander le bon périmètre sans lire d'abord les données protégées ? **Q2, Q3** |
| Interface de communication | Quelles opérations proposer à l'agent pour découvrir ses droits, demander un accès, consulter son état et agir dans son périmètre ? Que fournit MCP aujourd'hui et que faudrait-il ajouter autour ? Garder ouvertes les autres intégrations lorsqu'un besoin concret les justifie. **Q2, Q4, Q8** |
| Attente de l'humain et reprise | Que reçoit l'agent lorsqu'une demande attend une décision ? Comment reprend-il si la personne répond plus tard, si sa session se termine, ou si la notification manque ? Examiner refus, expiration, annulation, répétition de demande et résultat d'exécution incertain. **Q6, Q8** |
| Vie des accès | Comment l'agent apprend-il qu'un accès est suspendu, révoqué ou modifié ? Quel usage compte pour l'inactivité, notamment avec une tâche périodique ? Que deviennent le contexte déjà reçu et les opérations en cours ? **Q5, Q6, Q7** |
| Limites et contournements | Quels outils, secrets ou connecteurs parallèles permettraient d'éviter Moraine ? Comment traiter les modifications indirectes de périmètre, les droits combinés et les demandes insistantes ? Distinguer le client bien intégré d'un environnement agent réellement isolé. **Q4, Q7, Q8** |

L'identité et les droits doivent venir de faits authentifiés. Un nom, un
`approved=true` ou une instruction utilisateur rapportée par le modèle ne
constituent pas une preuve d'autorité. La demande d'extension d'accès peut être
une capacité agent; sa validation humaine reste indépendante. L'inspection
du contenu et les autorisations gardent des responsabilités distinctes.

## Manière de poursuivre

Commence par un bref rappel de ce que tu as compris, puis prends ce scénario
comme fil conducteur :

> J'utilise un assistant qui n'a encore aucun accès à ma messagerie. Je lui
> demande de m'aider avec mes courriels de travaux. Il doit passer par Moraine
> pour préparer une demande précise, que je peux confirmer sur mon téléphone.
> Ensuite, il peut travailler dans le périmètre accordé.

Fais apparaître les étapes, les acteurs, les informations nécessaires et les
premières inconnues, sans choisir d'avance le fournisseur ou le protocole final.
Introduis les questions à mesure que le scénario les rend concrètes. Aborde
un point important à la fois; explique les options et leurs conséquences sans
exiger une décision pour continuer à imaginer.

Identifie clairement ce qui est constaté dans le pilote, proposé pendant la
discussion, accepté explicitement ou encore inconnu. Vérifie dans les sources
officielles les capacités actuelles des clients ou protocoles lorsqu'une
conclusion en dépend; utilise la compétence `openai-docs` si le cas concerne
les capacités de Codex. Une compatibilité annoncée ne vaut pas une intégration
qualifiée avec Moraine.

Quand je demanderai de consigner les résultats, complète la note d'exploration
et les questions Q1 à Q8 concernées, en gardant les alternatives ouvertes et
les nouvelles questions apparues. Le résultat recherché est une compréhension
plus concrète du parcours côté agents, pas une spécification exhaustive à
produire d'un seul coup.
