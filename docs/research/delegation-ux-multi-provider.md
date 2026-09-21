# Délégation, autorisation humaine et gestion des accès

Date : **21 septembre 2026**. Statut : **exploration produit et documentaire**.
Cette note consigne la discussion sur l'accès à une partie d'une boîte email,
avec d'autres ressources possibles à terme. Elle distingue les attentes
exprimées des solutions proposées; elle ne vaut ni choix d'architecture
accepté, ni mandat d'implémentation.

La discussion reste volontairement ouverte : l'utilisateur souhaite continuer
à imaginer les usages avant de choisir entre briques logicielles, application
complète ou service. Les pistes produit portent sur une interface mobile ou
web, le suivi des accès inutilisés et un accès continu sans date de fin imposée.
La suite côté agents a retenu un premier essai borné avec Codex et un fournisseur
simulé; son [plan](../plans/agent-access-pilot.md) a ensuite été revu et son
exécution autorisée. Les choix produit plus larges restent ouverts.

## Besoin exprimé et difficulté actuelle

L'utilisateur veut donner un accès limité à un agent sans transformer cette
délégation en travail d'administration : ajouter et modifier chaque élément
autorisé dans une interface distincte serait trop lourd pour un usage courant.
La sécurité doit accompagner un geste compréhensible et peu coûteux.

Il précise que Gmail n'est qu'un fournisseur parmi d'autres : l'ambition est
de pouvoir supporter **potentiellement tous les grands fournisseurs**, sans
liste exhaustive, ordre de priorité ni équivalence fonctionnelle décidés.
La mention d'autres ressources reste une ouverture, sans périmètre arrêté.
Ces attentes proviennent de la conversation du 21 septembre 2026.

**Stockage et consentement sont distincts.** Moraine peut créer les
enregistrements nécessaires à partir d'un geste humain ou d'une règle déjà
autorisée. Une base de données n'impose pas l'édition manuelle de chaque ligne.
En revanche, il reste à concevoir où et comment l'humain exprime, comprend et
retire son consentement. L'automatisation du stockage ne crée aucun droit.

Le [contrat actuel](../pilot/interface.md) reçoit, par le canal humain,
des ressources synthétiques copiées et immuables : **1–5 messages**, une note
facultative, un destinataire fixé et une délégation de **30 minutes maximum**.
La [proposition d'ingestion](../plans/email-ingestion-contract.md), revue mais
non acceptée comme produit ni implémentée, conserve une sélection fermée et
exclut explicitement les filtres vivants. Le parcours du pilote ne constitue
donc pas encore l'expérience quotidienne recherchée.

## Deux modes de délégation explorés

| Mode | Geste et comportement envisagés | Conséquence d'usage |
| --- | --- | --- |
| Partage ponctuel | Sélectionner quelques messages pour une tâche; les nouveaux messages ne rejoignent pas automatiquement la sélection. | Périmètre facile à expliquer, mais geste à répéter et compléments à demander si le contexte manque. |
| Périmètre durable | Autoriser un espace ou une règle, par exemple les messages d'un dossier « Travaux maison », avec inclusion des ajouts si elle est consentie. | Moins d'interventions répétées; entrées, sorties, maintien de l'accès, suspension et révocation doivent être compréhensibles. Une date de fin n'est pas nécessairement imposée. |

**Aucun des deux modes n'a été choisi.** Ils pourraient coexister; la question
est notamment lequel servir en premier. L'exemple d'un dossier est une piste,
pas une définition acceptée du modèle d'autorisation.

Un droit de lecture durable n'accorde ni envoi autonome ni travail continu en
arrière-plan. Ces décisions restent indépendantes. Un périmètre évolutif
pourrait aussi conserver des captures exactes du contexte et un snapshot
d'action figé pour chaque approbation. C'est une possibilité de conception,
qui exige une évolution explicite du contrat actuel, pas une permission de
remplacer les octets approuvés par une version ultérieure.

## Où l'utilisateur agit

Un connecteur permet à Moraine de communiquer avec le fournisseur; il ne fait
pas apparaître automatiquement un bouton dans sa messagerie. Trois pistes
ont été distinguées :

- **Fonctions natives** : après configuration dans Moraine, classer les messages
  dans un dossier ou appliquer un libellé déjà disponible dans la messagerie.
- **Complément du fournisseur** : installer une interface Moraine intégrée,
  à développer et maintenir dans les limites de la plateforme.
- **Interface Moraine** : connecter les comptes, sélectionner les ressources
  ou définir les règles dans une interface commune séparée.

Google fournit effectivement des
[compléments affichés lors de la lecture d'un message](https://developers.google.com/workspace/add-ons/gmail/extending-message-ui).
Cela rend l'exemple « Partager avec mon assistant » envisageable pour Gmail,
sans constituer une solution universelle ni une fonctionnalité livrée.

## Configuration proposée par l'agent et autorisation mobile

Suite de l'exploration du **21 septembre 2026** : l'utilisateur propose de
demander simplement à l'agent de préparer les accès et réglages nécessaires.
Moraine, connecté aux services, appliquerait les changements après autorisation
humaine. Il identifie le risque que l'agent demande lui-même une extension de
ses droits sans instruction de l'utilisateur.

L'utilisateur propose ensuite une **application sur le téléphone** : une
demande d'autorisation reçue par Moraine déclenche une notification; la personne
ouvre les détails et accepte ou refuse. Cette piste est consignée comme
proposition, sans choix technique ni mandat d'implémentation. Elle pourrait
servir aux deux modes de délégation et offrir un canal humain commun aux
différents fournisseurs et agents.

Parcours envisagé :

1. L'agent soumet à Moraine une proposition structurée de configuration,
   sans obtenir de nouveaux droits à ce stade.
2. Moraine vérifie et fige les changements prévus, conserve la demande en
   attente et envoie une notification générique au téléphone associé.
3. L'utilisateur ouvre l'application, qui récupère directement auprès de
   Moraine les détails et l'état courant de la demande.
4. L'écran présente l'agent, les comptes, les ressources concernées, les droits,
   les conditions de maintien de l'accès (continu ou temporaire), l'inclusion
   éventuelle des futurs éléments et les modifications prévues chez les
   fournisseurs. La personne accepte ou refuse.
5. Moraine vérifie la décision authentifiée et applique uniquement les
   changements approuvés et encore autorisés. Les règles fines peuvent rester
   dans Moraine; modifier le fournisseur n'est pas nécessaire dans tous les cas.
6. L'application et l'agent reçoivent le résultat. Une approbation et une
   modification effectivement exécutée sont deux états distincts.

Une notification push peut alerter lorsque l'application est en arrière-plan;
elle n'est pas une preuve de consentement. Proposition : ne pas y placer les
détails sensibles, mais les récupérer dans l'application après authentification.
Le comportement dépend de la plateforme et des permissions de notification;
le choix du service push reste ouvert.
[Fonctionnement documenté de FCM](https://firebase.google.com/docs/cloud-messaging/customize-messages/set-message-type)

Le résumé de confirmation doit être construit par Moraine à partir des effets
réels prévus. Une justification de l'agent peut l'accompagner, sans remplacer
ces informations. Un champ « utilisateur approuvé » ou un message rapporté
par l'agent n'accorde aucun droit. La preuve d'approbation doit être liée à la
demande exacte, utilisable pendant un délai borné pour son activation et non
réutilisable pour une autre opération. Modifier la demande impose une nouvelle
confirmation. Cette échéance d'activation n'impose pas une date de fin à
l'accès accordé.
[Principes d'autorisation d'une opération](https://cheatsheetseries.owasp.org/cheatsheets/Transaction_Authorization_Cheat_Sheet.html)

Cette séparation suppose que l'agent ne contrôle ni le téléphone ni ses moyens
d'approbation. L'association initiale, le remplacement et la récupération de
l'appareil doivent rester sous contrôle humain. Une vérification biométrique
est une possibilité, pas un choix arrêté. Une page que l'agent peut manipuler
avec ses outils ne constitue pas à elle seule ce canal indépendant.

Sans réponse, la demande reste sans effet puis expire. Refuser n'accorde aucun
nouveau droit. Limiter les sollicitations éviterait des notifications répétées
incitant à accepter machinalement. Réserver les demandes à une session de
configuration ouverte par l'humain est une autre option évoquée, non décidée.
Les contrôles doivent aussi couvrir les chemins indirects, par exemple l'ajout
par l'agent d'un message dans un dossier qui lui donnerait accès à ce message.

Le [pilote actuel](../architecture.md) possède déjà un mécanisme de proposition
figée et d'approbation par un canal humain pour l'envoi. Il ne propose ni
modification des permissions par l'agent ni application mobile; l'isolation
réelle du canal humain reste à qualifier.

## Gérer les accès sur téléphone ou sur le web

L'utilisateur voit dans cette piste la possibilité d'une **interface de gestion
de ce qui est permis**, sur téléphone ou en ligne, avec notamment des
avertissements lorsqu'une ressource n'est plus utilisée depuis longtemps.
L'expérience pourrait couvrir l'octroi initial puis le suivi des délégations.

Fonctions envisagées, sans interface choisie ni fonctionnalité livrée :

- Voir quel agent peut accéder à quels comptes et ressources, avec quels droits.
- Consulter l'activité observée : dernière utilisation, opérations et refus.
- Suspendre un accès ou un agent, réduire son périmètre, révoquer une délégation.
- Repérer les accès inutilisés ou associés à une tâche qui semble terminée,
  et proposer de les conserver, de les suspendre ou de les retirer.

La mesure à définir est l'utilisation **d'un accès par un agent via Moraine**.
Une ressource peut être utilisée quotidiennement par son propriétaire tout en
étant inutilisée par l'agent. Moraine ne peut pas déduire l'usage global d'un
compte à partir des seules opérations qui passent par elle. L'identification
d'une tâche terminée reste aussi une piste, pas une capacité démontrée.

Une interface web éventuelle doit conserver les exigences du canal humain :
être accessible en ligne ne prouve pas que l'agent ne peut pas y approuver
lui-même une demande. Le mécanisme d'approbation indépendant reste à concevoir.

## Inactivité et suspension automatique

L'utilisateur propose l'analogie avec les applications inutilisées sur Android,
pour lesquelles il reçoit des notifications et constate une désactivation.
Android documente notamment le retrait des permissions et l'hibernation après
une période d'inactivité, avec des effets variables selon les versions. Cette
référence inspire le parcours; elle ne fixe pas la politique de Moraine ni une
séquence universelle de notifications Android.
[Hibernation Android](https://developer.android.com/topic/performance/app-hibernation)

Cycle exploré pour Moraine : une règle de suspension est annoncée lors de
l'octroi de l'accès; Moraine détecte l'inactivité, avertit de la suspension
prévue et suspend sans intervention si cette règle le prévoit. La reprise
demande une confirmation humaine. Les messages et documents restent chez leur
fournisseur; l'objet suspendu est l'autorisation d'accès.

Le choix entre rappel seul et suspension automatique, les délais, les exceptions
et les critères d'activité restent ouverts. Les durées mentionnées dans les
exemples de la conversation ne sont pas des seuils produit adoptés. Une
notification manquée ne vaut jamais consentement à un nouvel accès; une
suspension sans réponse applique une règle préalablement autorisée.

Une question subsiste : un appel ou une lecture artificielle de l'agent ne
devrait pas lui permettre de maintenir ses droits indéfiniment. Définir une
activité pertinente sans pénaliser les tâches légitimement automatisées reste
à explorer. Ce risque n'établit pas à lui seul qu'il faille imposer une date de
fin à toutes les délégations.

## Accès continu et durée facultative

**Réserve explicite de l'utilisateur :** demander une durée au moment de donner
l'accès lui paraît un choix étrange et peu naturel pour un usage régulier.
Son intuition sur ce que voudraient la plupart des personnes n'est pas une
étude utilisateur. Elle remet en question l'expiration systématique proposée
plus tôt, sans modifier la borne de 30 minutes du pilote actuel.

Le modèle proposé à la suite de cette réserve est un **accès continu par
défaut, révocable à tout moment**, dans le périmètre approuvé, avec une gestion
des accès oubliés. Un accès temporaire resterait facultatif pour les situations
qui le justifient. Ce défaut constitue une piste à poursuivre, pas une politique
implémentée ou une spécification produit acceptée.

Deux durées indépendantes doivent être distinguées :

| Notion | Sens envisagé |
| --- | --- |
| Validité de la demande et de sa preuve d'approbation | Délai technique borné pour empêcher une vieille demande d'activer une configuration devenue obsolète; Moraine le gère sans faire choisir une durée à l'utilisateur. |
| Durée de l'accès accordé | Peut rester continue jusqu'à révocation ou suspension selon les règles convenues; une date de fin explicite est une option. |

Un ajout de compte, de ressources ou de droits au-delà du périmètre consenti
demanderait une nouvelle approbation. Les nouveaux éléments entrant dans une
règle déjà approuvée suivent cette règle, si leur inclusion a été explicitée.
L'accès continu ne permet ni à l'agent d'élargir cette règle ni de réactiver
seul un accès suspendu.

## Possibilités documentées par fournisseur

Ces exemples illustrent des voies d'intégration, **aucun support Moraine
implémenté ou qualifié**. Sources consultées le 21 septembre 2026; leurs
conditions peuvent évoluer.

| Fournisseur | Voie documentée |
| --- | --- |
| Gmail / Google Workspace | API Gmail; filtrage des messages par libellés avec `labelIds`. [Google](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/list) |
| Outlook.com / Microsoft 365 | Microsoft Graph pour les messages, dossiers et catégories. [Microsoft](https://learn.microsoft.com/en-us/graph/api/resources/mail-api-overview?view=graph-rest-1.0) |
| iCloud Mail | IMAP pour la lecture, SMTP pour l'envoi. [Apple](https://support.apple.com/en-ie/102525) |
| Yahoo Mail | IMAP et SMTP, avec authentification propre au service. [Yahoo](https://help.yahoo.com/kb/SLN4075.html) |
| Fastmail | JMAP, ou IMAP pour lire et SMTP pour envoyer. [Fastmail](https://www.fastmail.com/dev/) |
| Proton Mail | IMAP/SMTP via Bridge installé localement; abonnement Proton Mail payant requis à la date consultée. [Proton](https://proton.me/support/imap-smtp-and-pop3-setup) |

Les fonctionnalités, l'authentification, les dossiers/libellés, l'identité des
messages et les modalités de révocation doivent être examinés par connecteur.
Par exemple, Microsoft signale que certains déplacements peuvent changer les
identifiants ordinaires des messages.
[Identités Graph](https://learn.microsoft.com/en-us/graph/api/resources/mail-api-overview?view=graph-rest-1.0)
La compatibilité avec un protocole ne qualifie pas un parcours produit.

## Orientation proposée et frontière de confiance

L'orientation discutée serait un cœur commun de délégation, inspection,
approbation, révocation et historique; des connecteurs et protocoles adaptés;
une interface commune pour les comptes et permissions. Les compléments
pourraient faciliter certains gestes sans être indispensables au fonctionnement
de base. **Cette orientation reste proposée.**

Avec le scope Gmail classique `gmail.readonly`, le connecteur reçoit un accès
de lecture large; `labelIds` filtre une requête et ne constitue pas une
permission OAuth limitée au libellé.
[Scopes Gmail](https://developers.google.com/workspace/gmail/api/auth/scopes)
La restriction envers l'agent devrait alors être appliquée par Moraine.
L'accès confié au service peut donc être plus large que celui confié à l'agent.
L'agent ne doit recevoir ni identifiants d'authentification du fournisseur ni
moyen d'élargir sa propre règle, y compris en modifiant les classements qui
déterminent son accès.

Pour un périmètre durable, il faut préciser qui peut y ajouter des messages,
si les règles automatiques de la messagerie comptent, et quand un retrait
coupe les accès futurs. La révocation ne rappelle pas les informations déjà
communiquées; cette limite figure aussi dans la
[proposition d'ingestion](../plans/email-ingestion-contract.md).

## Forme du projet et poursuite de l'exploration

L'utilisateur constate que l'ensemble envisagé ressemble de plus en plus à un
service qu'une entreprise pourrait proposer : connecteurs, interfaces, mobile,
notifications et gestion des comptes élargissent le périmètre du moteur de
sécurité. La discussion distingue l'ouverture du code et la prise en charge
du produit ou de son exploitation; un cœur open source, une application de
référence, un produit autonome ou une offre hébergée restent des possibilités.

**L'utilisateur ne souhaite pas trancher maintenant** entre développeurs
intégrateurs et utilisateurs finaux, ni choisir immédiatement une forme de
distribution. Il veut continuer à imaginer et voir où les usages mènent le
projet. Le séquencement de décisions proposé précédemment n'est donc pas une
feuille de route acceptée.

Restent ouverts pour le produit, sans ordre de décision imposé : les premiers
fournisseurs réels, les interfaces mobile/web, l'hébergement, le mécanisme
d'approbation et la récupération du téléphone, ainsi que les règles de
suspension et de réactivation. Les modes ponctuel et durable peuvent encore
coexister. Les idées consignées ne constituent pas une autorisation de lancer
leur implémentation.

## Suite côté agents : premier parcours retenu

Lors de la suite du **21 septembre 2026**, l'utilisateur précise qu'un assistant
pourrait être Codex, ChatGPT, Gemini ou un autre client. Il s'attend à ce qu'un
même agent réutilise son accès dans des conversations différentes. Le choix
d'un premier client ne définit pas une dépendance produit à ce client.

**Périmètre accepté pour préparer le plan :** Codex demande à Moraine l'accès
à une ressource, Moraine enregistre la demande, l'humain l'accepte localement
sans push ni application mobile, puis Moraine récupère des emails fictifs par
l'API d'un fournisseur simulé et les rend consultables par l'agent. L'utilisateur
a explicitement confirmé qu'un fournisseur simulé suffit. Une approbation et
des données effectivement disponibles restent deux faits distincts.

**Recadrage accepté :** Moraine est un petit pilote destiné à découvrir les
responsabilités. Un utilisateur réalisant le parcours suffit. L'idée de
plusieurs utilisateurs ayant chacun zéro ou plusieurs agents reste une
perspective; la montée en charge appartient à une éventuelle réécriture
informée par ces découvertes, sans exigence de grande échelle maintenant.

Le [plan du premier parcours](../plans/agent-access-pilot.md) propose une
sélection fixe, un grant de lecture seule, deux outils MCP supplémentaires,
une décision par la CLI humaine et une preuve dans deux conversations Codex.
Ces modalités ont été proposées dans le plan, puis soumises à une revue
indépendante. L'utilisateur a ensuite demandé « Exécute le plan » : ce lot
local est autorisé, sans publication Git ni intégration de fournisseur réel.
Voir le [guide du parcours](../pilot/agent-access.md) pour son exécution.
Pendant l'essai, l'utilisateur a précisé que le canal humain devait être
simulé : l'opérateur de test relaie la décision via la CLI/socket, sans
réception de demande par une personne ni qualification du consentement réel.

## Questions à reprendre

Le **21 septembre 2026**, l'utilisateur demande de conserver les huit points
ci-dessous pour y revenir. **Les choix produit restent ouverts; les précisions
du premier essai sont consignées ci-dessous.** Les numéros permettent
de les retrouver; ils ne fixent ni priorité ni ordre de décision. L'accord
porte sur les sujets à explorer, pas sur une réponse ou une implémentation.

### Q1 — À qui accorde-t-on l'accès ?

L'autorisation vise-t-elle une application, un agent particulier ou une tâche ?
Que devient-elle si l'agent utilise des sous-agents ou change de fournisseur
de modèle ? Comment le nom présenté à l'utilisateur correspond-il à une
identité authentifiée et au destinataire réel des informations ?

Précision exprimée : un même agent doit pouvoir réutiliser son accès entre
conversations. Le plan propose une identité configurée unique pour l'essai;
association des comptes, sous-agents et changement de modèle restent ouverts.

### Q2 — Comment traduire une demande naturelle en permission précise ?

« Donne accès à mes courriels de travaux » ne définit pas encore les messages,
pièces jointes et futurs échanges inclus. Comment lever ces ambiguïtés et
produire une confirmation compréhensible, sans laisser une interprétation
approximative élargir les droits ?

### Q3 — Que peut découvrir l'agent avant l'autorisation ?

Pour proposer un dossier, l'agent pourrait vouloir connaître les dossiers
disponibles; pour retrouver des messages, il pourrait vouloir lire la boîte.
Comment préparer une demande utile sans lui divulguer d'avance le contenu ou
les métadonnées qui doivent justement être autorisés ?

Pour l'essai, le plan propose un nom public de sélection configuré par
l'opérateur, sans inventaire préalable de la boîte. Cela permet d'observer
la demande sans résoudre la découverte générale ni l'interprétation de Q2.

### Q4 — Quelles opérations exigent une nouvelle confirmation ?

Lecture et envoi sont déjà distingués, mais le classement, la suppression,
le téléchargement et le partage vers un autre service restent à examiner.
Comment traiter la combinaison de droits qui, séparément, semblent acceptables ?
Exemple à explorer : lire des documents privés et pouvoir envoyer des messages.

### Q5 — Comment gérer les changements de périmètre et l'inactivité ?

Quand un message entre dans un dossier ou en sort, à quel moment son accès
change-t-il ? Comment distinguer un accès oublié d'une tâche légitime exécutée
une fois par mois ? Quels signaux d'activité utiliser sans permettre à l'agent
de maintenir artificiellement ses droits ?

### Q6 — Que se passe-t-il en cas de panne ou de perte d'accès ?

Téléphone perdu, notification manquée, fournisseur déconnecté ou modification
réussie dans un compte mais échouée dans un autre : quels états montrer et
comment permettre une récupération sûre ? Comment distinguer une approbation
reçue de changements effectivement appliqués ?

Pour l'essai accepté, montrer séparément accord humain et disponibilité des
données. Le plan propose une consultation persistante et un échec de
récupération explicite, sans nouvelle tentative automatique.

### Q7 — Où tourne Moraine et quelles données conserve-t-elle ?

Ordinateur de l'utilisateur, serveur personnel ou service opéré : quelles
conséquences pour la disponibilité depuis le téléphone et la responsabilité
sur les identifiants d'authentification, copies de messages et historiques ?
Que conserve-t-on après retrait d'un accès, et comment expliquer que la
révocation ne rappelle pas les informations déjà transmises ?

### Q8 — L'expérience est-elle réellement comprise et utilisable ?

Les personnes comprennent-elles les confirmations, le périmètre de leurs
autorisations et les avertissements d'inactivité ? À partir de quand les
sollicitations deviennent-elles encombrantes ou acceptées machinalement ?
L'appréciation de l'équipe ne remplace pas l'observation d'utilisateurs.

Première observation retenue : demander, accepter localement et lire par
Moraine depuis Codex avec un fournisseur simulé. Ce parcours réduit ne
qualifie pas l'expérience mobile ni les usages de plusieurs utilisateurs.

Piste pour les explorer : raconter ou essayer des parcours concrets de première
connexion, d'extension d'accès, d'accès oublié et de téléphone perdu. Cela
permettrait de préciser les règles sans choisir immédiatement une architecture
ou un modèle commercial. Les réponses futures pourront être consignées sous
ces repères, avec leur statut proposé ou accepté et les éléments qui les étayent.

## Vérifications et limites

Les contrats locaux et les sources officielles citées ont été relus.
Pour Yahoo, l'ouverture directe a échoué; les paramètres ont été confirmés
par l'extrait indexé de sa documentation officielle. Les liens locaux ont
été contrôlés. Aucun compte distant connecté, modèle exécuté, envoi réel ou
test d'intégration n'a été réalisé. Cette note ne change ni le pilote ni le
statut des plans existants.
