# Appliquer les permissions dans une passerelle pour agents

Date : **22 septembre 2026**. Statut : **note de conception et de reprise**.
Elle consigne la discussion avec l'utilisateur : orientations retenues,
propositions à préciser et questions ouvertes. Elle ne constitue pas une
spécification acceptée, un mandat de développement ou une validation technique.

**Question centrale : comment Moraine peut-elle contrôler réellement les
opérations d'un agent, tout en lui laissant la liberté de rechercher, lire et
recouper les informations nécessaires à son travail ?** L'utilisateur identifie
l'application des permissions comme le cœur de la difficulté du projet.

## 1. Direction retenue et statut des propositions

| Sujet | Statut à la fin de la discussion |
| --- | --- |
| Commencer par les particuliers, avec une évolution possible vers l'entreprise | Orientation de travail acceptée; premier usage, offre et modèle commercial non choisis |
| Moraine comme passerelle ou proxy qui applique les permissions | Direction explicitement confirmée par l'utilisateur |
| Inspecter les requêtes et leurs paramètres pertinents, notamment les termes de recherche | Exigence exprimée; point d'interception et couverture technique à définir |
| Permettre une recherche progressive, sans sélection manuelle préalable de chaque message | Besoin exprimé; aucune recherche générale implémentée dans le pilote |
| Règles générales, par exemple recherches autorisées et envois soumis à accord | Proposition de l'utilisateur à développer; aucun défaut produit fixé |
| Journal compréhensible de l'activité passée par Moraine | Fonction envisagée; contenu, conservation et niveau de preuve à définir |
| Réutiliser les outils/connecteurs existants | Piste de conception pour éviter de reconstruire leurs capacités; compatibilité et garanties à vérifier |

Le travail sur Arcade/Workato avait trop centré la discussion sur une
comparaison technique. Le [bilan partiel](../../pilot-results/competitive-comparison/20260921-access-preparation/REPORT.md)
reste une preuve documentaire datée, avec **aucun essai produit externe**.
Il ne mesure ni la valeur du futur produit ni sa position face aux offres en
production. Les informations sur les offres existantes peuvent éclairer une
réutilisation; le prototype Moraine n'est pas leur équivalent commercial.

## 2. Scénario de référence : retrouver les échanges sur la toiture

L'utilisateur propose : « Trouve tous mes emails qui parle de refaire mon
toit et résume où on en est ».

Une recherche utile peut nécessiter plusieurs étapes : chercher « toiture »,
trouver le nom d'un entrepreneur, rechercher ses échanges, lire un devis,
retrouver une pièce jointe, puis vérifier si un message ultérieur change la
décision. L'agent doit pouvoir reformuler et recouper. Une autorisation limitée
à un dossier déjà préparé ou à une liste de messages choisie manuellement ne
suffit pas comme unique mode d'utilisation.

Deux frictions sont à éviter : demander un accord pour chaque reformulation
alors qu'une permission existante couvre l'opération, et présenter une absence
d'autorisation comme une absence d'information. « Je n'ai pas pu chercher »
et « cette recherche n'a rien trouvé » sont des résultats différents.

Le mot « tous » demande aussi de rendre compte de la couverture : boîtes
interrogées, filtres, pagination achevée ou partielle, contenus non inspectés
et échecs. Une recherche sans résultat ne prouve pas que l'information
n'existe nulle part. Ces informations doivent aider l'agent à décider de la
suite sans inventer un résultat.

## 3. Répartir les responsabilités

| Rôle proposé | Responsabilité |
| --- | --- |
| Agent | Conduire l'exploration, choisir les requêtes, lire, recouper et produire le bilan |
| Moraine | Authentifier l'appelant, déterminer les droits applicables, contrôler l'opération, obtenir un accord si nécessaire, suivre l'exécution et conserver sa trace |
| Outil ou connecteur | Traduire et exécuter les opérations auprès du fournisseur, dans un cadre que Moraine peut effectivement contrôler |
| Fournisseur | Appliquer ses propres droits et exécuter ses fonctions de recherche, lecture ou modification |
| Personne autorisée à décider | Définir les règles, accorder ou retirer les délégations, approuver les actions qui l'exigent |

L'intention est de préserver le rôle d'intermédiaire de Moraine : elle reçoit
une demande, vérifie l'autorisation, fait récupérer ou traiter les données,
puis retourne le résultat permis. Réutiliser un connecteur peut être une
façon de réaliser cette exécution. Cela ne permet pas d'abandonner le contrôle
des effets derrière un outil opaque.

Moraine n'a pas vocation, dans cette direction, à devenir un second agent
chargé de résoudre lui-même toutes les recherches, ni à construire d'office
un moteur de recherche universel. Elle doit néanmoins comprendre suffisamment
les opérations exposées pour leur appliquer des permissions fiables. Le
travail d'intégration et de qualification ne disparaît donc pas.

## 4. Vocabulaire de travail

Ces termes servent à poursuivre la conception; ils ne définissent pas encore
un schéma de données ou une interface logicielle.

- **Règle de permission** : choix permettant, interdisant ou soumettant à
  accord une catégorie d'opérations dans un périmètre identifié.
- **Délégation** : droits utilisables par une identité agent reconnue, sur
  certains comptes ou ressources, selon les règles applicables.
- **Requête** : demande concrète avec une opération et ses paramètres. Il faut
  préciser si l'on parle de l'appel d'outil ou d'un appel fournisseur interne.
- **Décision d'accès** : résultat du contrôle d'une requête à cet instant.
- **Approbation d'action** : accord portant sur une opération précise à
  exécuter; elle n'accorde pas implicitement tous les droits de cette catégorie.
- **Observation d'exécution** : fait constaté sur la tentative, les données
  transmises ou le résultat; distinct de la demande et de son autorisation.

Une connexion fournisseur donne une capacité technique. Elle ne signifie pas
que chaque agent peut exercer tous les droits associés. L'identité authentifiée
de l'agent, le compte source, le propriétaire et l'approbateur sont des notions
distinctes, même si une personne cumule plusieurs responsabilités.

## 5. Des règles générales avec contrôle de chaque requête

L'utilisateur propose : « autoriser toutes les recherches » comme réglage
global, tout en demandant la permission avant d'envoyer quelque chose.

**Une autorisation générale évite les confirmations répétées; elle ne supprime
pas le contrôle.** À chaque appel, Moraine doit encore vérifier l'identité,
le compte, l'opération réelle, les paramètres et les droits encore valides.
L'examen d'une requête structurée n'exige pas nécessairement un modèle d'IA.

Exemple à discuter, **sans valeur de configuration ou de défaut adopté** :

| Opération | Règle possible |
| --- | --- |
| Rechercher dans une boîte désignée | Autoriser automatiquement les recherches successives |
| Lire les messages trouvés | Autoriser si ce droit de lecture a également été accordé |
| Télécharger des pièces jointes | Choix distinct à préciser |
| Envoyer un message | Demander un accord sur l'envoi exact |
| Supprimer ou modifier des messages | Interdire ou demander un accord selon le choix humain |

« Global » reste à préciser : règle par défaut de la personne, ensemble
d'agents, compte donné ou plusieurs comptes explicitement inclus. Ce mot ne
doit pas devenir une permission implicite sur toute connexion présente.
Exceptions, priorités entre règles et comportement sans règle restent ouverts.

Une recherche peut déjà exposer sujets, expéditeurs, extraits ou corps. Il faut
donc définir ce que le droit de recherche autorise à transmettre, sans supposer
que seul un appel nommé « lire » révèle de l'information. De même, une lecture
peut avoir un effet annexe, par exemple modifier un état de lecture selon
l'outil utilisé : la classification doit suivre les effets réels.

### Termes de recherche et périmètre autorisé

Moraine doit disposer des paramètres nécessaires à ses contrôles : requête,
filtres, compte ciblé, identifiants, destinataires ou contenu selon l'opération.
Le nom de l'outil ou la justification textuelle de l'agent ne suffisent pas.

Il faut distinguer trois exigences :

1. **Voir les termes** pour comprendre et journaliser la requête.
2. **Restreindre des paramètres** selon une règle vérifiable, par exemple un
   compte, une opération ou des destinataires autorisés.
3. **Garantir un thème**, comme « uniquement les messages sur mon toit ».
   Cette dernière exigence n'est pas résolue par la présence de certains mots.

Une recherche sur « toiture » peut retourner des informations sans rapport;
une recherche sur le nom d'un entrepreneur peut être nécessaire sans contenir
ce mot. Le thème de la tâche guide l'agent, mais ne forme pas automatiquement
une limite de sécurité précise. Aucun filtrage sémantique général n'est choisi.

## 6. Où placer le contrôle pour qu'il soit réel ?

L'exigence exprimée est d'inspecter les requêtes pertinentes pour les droits.
**Le niveau auquel cette exigence sera assuré n'est pas encore décidé.**

| Point de contrôle envisagé | Visibilité | Difficulté à résoudre |
| --- | --- | --- |
| Entre agent et outil/connecteur | Appel d'outil, paramètres et résultat exposés | Un appel peut déclencher plusieurs appels fournisseur ou des effets non visibles à ce niveau |
| Entre connecteur et fournisseur | Requêtes API effectivement émises et réponses | Comprendre les opérations fournisseur et garantir que les chemins concernés passent par Moraine |
| Combinaison des deux | Demande de l'agent et exécution détaillée | Relier les deux sans dupliquer ou contredire les décisions |

Ce sont des options de conception, pas trois modes promis. L'analogie du VPN
exprime un passage contrôlé; elle ne prouve pas qu'un simple tunnel réseau
permet de comprendre les opérations ou d'inspecter du trafic chiffré.

Pour un connecteur réutilisé, examiner notamment recherche, pagination,
lecture des fils, pièces jointes, opérations groupées, caches et sous-appels.
L'étiquette « recherche » ne doit pas couvrir silencieusement un envoi ou
une modification. Si une opération ne peut pas être comprise ou contrôlée,
la proposition est de signaler cette limite et de ne pas la présenter comme
protégée; le traitement produit exact reste à décider.

Les accès concernés doivent passer par le contrôle. Si l'agent possède aussi
un autre accès direct au fournisseur, Moraine ne peut pas prétendre couvrir
ce chemin. Détention des identifiants, accès directs, isolation et confiance
accordée aux connecteurs devront être définis pour le montage retenu.

Contrôler la requête peut aussi être insuffisant pour une restriction sur les
ressources retournées : les réponses et métadonnées peuvent nécessiter un
contrôle avant transmission. Un contrôle après exécution ne peut toutefois
pas annuler un envoi déjà effectué; les opérations à effet doivent être
autorisées avant leur déclenchement.

## 7. Parcours proposé de décision et d'exécution

Cette séquence articule les responsabilités; elle n'est pas un contrat livré.

1. **Recevoir et identifier.** Relier l'appel à une identité authentifiée et
   déterminer l'opération, les paramètres et le compte réels. Ne pas prendre
   un champ fourni par l'agent pour une preuve d'autorité.
2. **Évaluer les droits.** Examiner la délégation et les règles courantes,
   avec les droits source. Une règle Moraine ne peut élargir les droits que
   le fournisseur autorise réellement.
3. **Autoriser, refuser ou demander un accord.** Une opération déjà couverte
   se poursuit sans interruption humaine. L'attente d'un accord n'exécute
   pas l'opération et n'est pas un résultat de recherche vide.
4. **Exécuter ce qui est autorisé.** Pour un envoi approuvé, conserver le lien
   entre accord et destinataires, contenu et pièces jointes exacts. Vérifier
   les droits encore valides avant l'effet; changer l'action ne réutilise pas
   silencieusement l'ancien accord.
5. **Contrôler la restitution.** Transmettre les données permises avec les
   informations utiles sur leur source et sur les limites de l'opération.
6. **Enregistrer et expliquer.** Distinguer demande, décision, tentative,
   réponse fournisseur, données transmises et éventuel effet confirmé.

Les protections existantes d'approbation sur snapshot/digest/nonce, de contrôle
avant IO et de résultat `unknown` constituent des références du pilote à
préserver; elles ne démontrent pas ce parcours général chez des fournisseurs
réels. Une issue incertaine ne doit pas devenir un succès ou une nouvelle
tentative automatique susceptible de dupliquer l'effet.

## 8. Ce que Moraine doit dire à l'agent et à la personne

| Situation | Information à rendre explicite |
| --- | --- |
| Accès manquant ou refusé | La recherche ou l'opération n'a pas été exécutée dans ce périmètre |
| Approbation en attente | Demande enregistrée, sans nouvel accès ou effet accordé par cette attente |
| Recherche exécutée sans résultat | Aucun résultat trouvé dans la recherche et le périmètre indiqués |
| Recherche incomplète | Sources, pages ou contenus non couverts, erreur ou interruption |
| Opération exécutée | Résultat observé et références disponibles |
| Résultat incertain | Tentative connue, effet final non établi |

Ces distinctions réduisent les ambiguïtés; elles ne garantissent pas à elles
seules le comportement correct de tout modèle client. Il faudra observer les
appels réels et la façon dont l'agent utilise ces états.

Le journal envisagé relierait : identité agent, utilisateur, compte,
horodatage, opération et paramètres utiles, règle/délégation appliquée,
décision, approbation éventuelle, tentative et résultat. Pour une recherche,
les termes peuvent être utiles à la restitution, tout en constituant des
données sensibles. Journaliser n'implique pas copier tous les emails.

Exemple fictif de bilan : « Cet assistant a effectué quatre recherches.
Moraine lui a transmis douze messages. Une tentative d'envoi a été bloquée. »
Ce bilan devra être dérivé des événements enregistrés, pas de ce que l'agent
affirme avoir fait. Moraine observe les données transmises, pas leur
compréhension ou tous leurs usages ultérieurs. Une acceptation fournisseur
ne prouve pas nécessairement l'effet final; cette limite doit rester visible.

Contenu, expurgation, accès au journal, durée de conservation, intégrité et
export restent à concevoir. Les secrets d'authentification n'y ont pas leur place.

## 9. Modularité utile : particuliers d'abord, entreprise possible

L'orientation est de développer une expérience personnelle utile tout en
préservant des possibilités d'évolution. Les séparations proposées sont :

- **Origine des règles et responsabilités** : une personne décide pour ses
  comptes; une organisation pourrait encadrer ce que chacun peut déléguer.
  Ne pas supposer partout que propriétaire, utilisateur et approbateur sont
  nécessairement la même identité. Les règles de priorité restent ouvertes.
- **Contrôle et exécution des outils** : conserver la décision d'accès
  distincte de la traduction fournisseur, avec un contrat permettant de
  vérifier ce que l'exécution fait réellement.
- **Parcours humain et décision** : une interface personnelle simple peut
  évoluer vers plusieurs rôles sans changer le sens de l'approbation.

Un service pour particuliers doit déjà séparer les comptes, données et secrets
de ses clients. Cette isolation n'est pas une option réservée à l'entreprise.
En revanche, SSO d'organisation, administration collective, déploiements privés
et exports spécialisés ne sont pas des livraisons décidées pour le premier lot.

Ces séparations n'imposent ni microservices ni système de plugins universel.
Leur intérêt devra être éprouvé sur les variations réellement nécessaires.

## 10. État du pilote et documents utiles

Le [contrat actuel](../pilot/interface.md) et
l'[architecture actuelle](../architecture.md) décrivent un broker avec identité
agent configurée, ressources synthétiques sélectionnées, captures fixes,
lecture contrôlée et approbation d'envoi. Le
[parcours d'accès](../pilot/agent-access.md) récupère les objets fictifs après
accord puis les rend lisibles, y compris dans une nouvelle conversation.

Il n'implémente pas une recherche générale, les règles utilisateur proposées
ici, un proxy universel de connecteurs ou la qualification d'un fournisseur
email réel. La limite des sélections du pilote ne doit pas devenir une limite
produit implicite. Les preuves restent celles du
[rapport du lot](../../pilot-results/codex-email/20260921-agent-access/REPORT.md);
aucun test métier n'est relancé pour cette note.

La [note d'exploration précédente](delegation-ux-multi-provider.md) reste utile
pour les accès continus, la révocation, l'inactivité et les huit questions
ouvertes. La présente note précise surtout Q1–Q4 et la façon d'appliquer les
permissions. **Inspection des permissions, inspection du contenu entrant et
détection d'injections restent des responsabilités distinctes.** Le
[contrat d'ingestion proposé](../plans/email-ingestion-contract.md) ne devient
pas une implémentation du seul fait de cette direction de passerelle.

## 11. Reprendre la discussion dans une autre session

La prochaine session peut partir de cette note, de l'index documentaire, du
contrat courant et de l'exploration précédente. Le mandat est de **continuer
la conception avec l'utilisateur, une décision importante à la fois**.
La création de cette note n'autorise ni développement, ni compte distant,
ni OAuth, ni dépense, ni essai fournisseur, ni commit/push. Il n'est pas
nécessaire de reprendre la campagne comparative pour poursuivre la réflexion.

**Premier sujet proposé : définir le contrat minimal d'une requête inspectable
sur le scénario « recherches autorisées, envoi soumis à accord ».** Décrire les
informations dont Moraine a besoin et les effets qu'elle doit contrôler,
puis choisir où les observer dans une intégration concrète. Ne pas choisir
le niveau MCP ou HTTP sur la seule analogie du proxy.

Questions suivantes à conserver, sans réponses présumées :

1. Quelle portée exacte pour une règle globale, ses exceptions et son retrait ?
2. Qu'autorise la recherche à révéler avant une lecture explicite ?
3. Comment vérifier les effets d'un connecteur et ses appels internes ?
4. Quel état retourner pour un appel inconnu, partiellement contrôlable ou refusé ?
5. Quelle approbation présenter pour un envoi exact et comment gérer sa reprise ?
6. Quelles preuves et quelles données personnelles conserver dans le journal ?
7. Quelle petite intégration permettrait d'éprouver la conception sans
   reconstruire un moteur de recherche ou une plateforme d'entreprise ?

Un futur essai, s'il est autorisé, devrait notamment montrer une recherche en
plusieurs étapes sans confirmations inutiles, un refus explicite, un envoi
bloqué avant accord et une trace distinguant les demandes des effets. Cela
reste une piste de validation, pas une campagne lancée par ce document.

Les orientations produit de cette note proviennent de la conversation des
21–22 septembre 2026. Les constats sur le pilote proviennent des documents
locaux liés, relus le 22 septembre. Aucune nouvelle recherche commerciale,
compatibilité de connecteur ou promesse de contrôle sémantique n'est établie ici.
