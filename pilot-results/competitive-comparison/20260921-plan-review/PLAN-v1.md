# Comparer un parcours d'accès agent à Arcade et Workato

Date : **21 septembre 2026**. Statut : **plan proposé, exécution non autorisée**.
Mandat courant : rédiger ce plan et le soumettre à un autre agent reviewer.
La recherche publique et la revue du plan ne constituent ni un essai produit,
ni une validation commerciale. Aucun compte, achat, installation ou contact
fournisseur n'est nécessaire pour terminer ce mandat.

## 1. Question et résultat attendu

Le [rapport de marché](../research/enterprise-agent-access-market.md) établit
un recouvrement documentaire important. L'expérience proposée doit répondre :
**les offres existantes permettent-elles déjà à une personne d'utiliser deux
agents avec des accès distincts, persistants et révocables, avec un effort
raisonnable de préparation par l'entreprise ?**

Le résultat doit pouvoir conduire à réutiliser une offre, à rechercher une
fonction complémentaire, ou à poursuivre une hypothèse Moraine. Il n'est pas
construit pour démontrer la supériorité de Moraine. Une friction observée n'est
pas encore un besoin commercial, et aucun entretien client n'est inclus.

Un seul parcours, une personne fictive, deux agents et une source de documents
suffisent. Jira, les écritures, l'envoi d'email, la montée en charge, les attaques
contre les fournisseurs et les performances générales restent hors de cet essai.
Le choix entreprise pour cette comparaison ne tranche pas le public du produit;
la pertinence pour les particuliers sera une hypothèse séparée.

## 2. Deux candidats et une référence limitée

| Candidat proposé | Motif de sélection | Condition à établir avant tout essai |
| --- | --- | --- |
| **Arcade** | Passerelle, plusieurs clients MCP, identité utilisateur et contrôles contextuels : proximité directe avec l'idée Moraine. | Édition donnant accès à l'identité, aux politiques et aux preuves nécessaires; essai gratuit ne signifie pas fonctions Enterprise incluses. |
| **Workato Enterprise MCP** | Configuration administrée, groupes, outils et accès au service sous l'identité utilisateur : alternative de plateforme intégrée. | Workspace avec MCP, Workato Identity et Verified User Access (VUA) utilisables; connexion Confluence Cloud compatible avec VUA à confirmer. |

Sources : [déploiement Arcade](https://docs.arcade.dev/en/operate/quickstart),
[contrôles Arcade](https://docs.arcade.dev/en/operate/governance/contextual-access),
[passerelle Workato](https://docs.workato.com/en/mcp/mcp-gateway),
[VUA Workato](https://docs.workato.com/en/mcp/verified-user-access).
Les conditions publiques ont été vérifiées dans la
[note de prérequis](../research/agent-access-comparison-prerequisites.md).
Arcade propose une entrée gratuite mais liste SSO/RBAC/audit dans Enterprise;
Workato inclut MCP dans Free sans établir toutes les fonctions nécessaires.
La fiche d'exécution devra confirmer l'accès effectif :
[tarifs Arcade](https://www.arcade.dev/pricing/),
[offre Workato](https://www.workato.com/free).

Les deux candidats restent les mêmes si un accès d'essai est indisponible :
le résultat est alors partiel et la ligne concernée reste « non essayée ».
Obot pourrait faire l'objet d'un remplacement explicitement décidé plus tard;
aucune substitution silencieuse par un produit plus facile à tester.

**Moraine est une référence de mécanismes, pas un troisième produit équivalent.**
Au commit `29a883450f585fc6662e151de133559670fc5864`, son
[contrat](../pilot/interface.md) configure une identité agent, des captures
fixes et des droits de 30 minutes. La [preuve conservée](../../pilot-results/codex-email/20260921-agent-access/REPORT.md)
couvre deux conversations de cette même identité, un fournisseur fictif et
une décision simulée. Elle ne couvre pas deux agents, Confluence ou un annuaire.
On ne modifie pas Moraine et on ne lance pas deux brokers pour prétendre
avoir démontré une gestion commune de plusieurs agents. Sa ligne utilisera
les preuves historiques avec ces limites; pas de nouveau classement de vitesse
ou d'ergonomie face aux produits.

## 3. Contrat commun à figer avant la configuration

Un administrateur **O** prépare l'environnement. Un employé fictif **U** utilise
deux agents logiques **A** et **B**. A et B peuvent employer le même logiciel
client MCP dans des configurations séparées. Ce montage teste deux délégations,
pas la compatibilité avec deux marques d'assistants.

L'identité amont doit rester U. Documenter séparément identité utilisateur,
identifiant du client, principal agent s'il existe, connexion fournisseur,
périmètre et objet de révocation. Un nom dans le prompt n'est pas une identité.
Le contrôle de A/B doit être rattaché côté serveur à une preuve authentifiée.
Changer seulement l'URL, cacher un outil dans le client ou créer deux employés
ne remplit pas cette condition. Les droits de U chez le fournisseur ne doivent
pas être modifiés pour simuler des restrictions propres à A/B.

**Source proposée : un tenant Confluence Cloud d'essai**, distinct de tout
espace professionnel ou personnel réel. Le même corpus fictif et la même
matrice de droits servent aux deux candidats. Chaque campagne conserve sa
configuration et ses connexions séparément pour éviter les effets croisés.
Les chemins retenus nécessitent de préparer les applications OAuth Atlassian,
leurs callbacks et scopes, puis le consentement de U. Pour Workato, retenir
**User's connection** avec VUA, jamais un jeton API ni une recette imbriquée
revenant au compte de service. Pour Arcade, ne pas prendre le mode Headers
avec identifiant fourni par le client pour une authentification indépendante.
Ces limites proviennent des guides
[Atlassian pour Arcade](https://docs.arcade.dev/en/references/auth-providers/atlassian),
[passerelles Arcade](https://docs.arcade.dev/en/operate/governance/mcp-gateways),
[Confluence Workato](https://docs.workato.com/en/mcp/prebuilt-mcps/confluence-mcp-server)
et [VUA](https://docs.workato.com/en/mcp/verified-user-access).

| Ressource fictive | Droit source de U | Agent A | Agent B |
| --- | --- | --- | --- |
| D1 — Plan du projet Atlas | Lecture | Lecture | Lecture |
| D2 — Budget Atlas | Lecture | Lecture | Refus |
| D3 — Autre projet, témoin exclu | Lecture | Refus | Refus |
| D4 — Espace réservé à O | Refus | Refus | Refus |

Les quatre textes, titres et identifiants ont des marqueurs synthétiques uniques.
D1 et D2 doivent permettre une synthèse utile. D3 vérifie une restriction plus
étroite que les droits source; D4 vérifie la conservation des droits source.
Tester les corps **et** les métadonnées par les surfaces exposées (recherche,
liste, lecture directe par ID). Le cas de lecture directe ne dépend pas d'une
recherche préalable. Rien dans ce plan ne permet un test sur les données
d'autres utilisateurs ou un service tiers hors du tenant autorisé.

## 4. Préparation et autorisation de l'essai

La phase documentaire doit produire une fiche concrète par candidat avant de
solliciter un accès : édition, URL officielle, fonctions requises, versions,
tenant disponible ou à créer, administrateur requis, IdP éventuel, client MCP,
connexion Confluence, scopes demandés, coût et conditions connues. Une valeur
inconnue reste inconnue; ni l'absence de documentation ni un refus commercial
ne prouvent l'absence d'une fonction.

Le mandat actuel s'arrête au plan revu. Pour une exécution ultérieure, vérifier
les autorisations déjà données puis obtenir uniquement celles qui manquent :
création/utilisation des comptes nommés, upload du corpus fictif, connexions
OAuth/SSO, configuration temporaire des clients et appels aux services/modèles.
Budget proposé : **aucune nouvelle dépense sans montant explicitement accepté**.
Un essai exigeant une carte, une commande ou un contact commercial ne sera pas
activé par défaut. Aucun email au fournisseur sans instruction explicite.

Après autorisation, utiliser exclusivement les environnements d'essai désignés.
Installer les dépendances éventuelles dans un environnement privé temporaire;
ne pas modifier de configuration agent globale. Les secrets et exports bruts
restent hors Git. L'opérateur de test peut jouer O et U; cela mesure le parcours
et le protocole, pas la compréhension d'un employé indépendant.

**Borne proposée :** au plus trois heures de préparation active par offre,
puis deux heures pour les scénarios et contrôles. Séparer le temps de lecture,
de configuration et les attentes externes. Un blocage de licence, d'IdP ou
d'identité A/B arrête le scénario dépendant, sans empêcher les observations
indépendantes. Au-delà de cette borne, livrer un résultat partiel et la cause;
ne pas lancer un développement pour finir à tout prix.

## 5. Protocole d'observation

Commencer avec les fonctions et réglages documentés du produit. Un filtrage
dans le script de test ou le prompt ne compte jamais comme un contrôle de
l'offre. Si une extension, un hook ou une recette sur mesure est nécessaire,
la décrire et estimer le travail séparément. Sa réalisation n'appartient pas
à ce premier essai; un résultat documenté avec extension n'est pas un succès
observé du produit standard. Consigner aussi les options commerciales ou
documentées qui pourraient changer le résultat.

Les contrôles directs utilisent un client MCP de test pour inspecter les
réponses, sans filtrer les données. Une exécution depuis un client agent natif
confirme ensuite le parcours utilisateur lorsque disponible et autorisé.
Conserver les outils effectivement appelés : une phrase de l'assistant ou un
refus volontaire du modèle n'est pas une preuve d'autorisation serveur.

| Étape | Geste à réaliser | Observation et critère |
| --- | --- | --- |
| S0 — Contrôle de la source | O crée le corpus; U consulte directement la source. | U lit D1–D3 et ne lit pas D4. Conserver état initial, IDs, versions et droits source. Si ce contrôle manque, les refus ultérieurs ne peuvent pas être attribués correctement. |
| S1 — Préparation administrée | O configure connexions, droits et rattachements A/B; U ouvre son client. | Compter séparément gestes O, authentifications/consentements U et modifications manuelles de configuration U. Vérifier la portée exacte des identifiants, pas seulement les écrans de configuration. |
| S2 — Accès distincts | A et B lisent D1, tentent D2 puis D3/D4, par ID et via les surfaces de découverte exposées. | Réponses conformes à la matrice. Toute divulgation hors périmètre est un écart, même si le résumé final l'omet. Si le produit n'a pas d'identité A/B distincte, noter la limite et ne pas présenter deux utilisateurs comme un succès. |
| S3 — Nouvelle conversation | Fermer les conversations et ouvrir un contexte vide pour chaque agent, en conservant son identité configurée. Redemander les mêmes lectures. | A/B retrouvent chacun leurs droits sans intervention nouvelle de O. Noter les réauthentifications U éventuelles, les appels source et la nature des données (capture, cache ou lecture actuelle). Une récupération à chaque lecture n'est pas pénalisée face aux captures Moraine. |
| S4 — Extension demandée | B demande D2 par le mécanisme disponible; aucune décision n'est prise. | D2 reste inaccessible tant qu'aucun changement autorisé n'est appliqué. Consigner demande durable, état consultable et rôle habilité, ou l'absence de parcours natif documenté. Une permission préalable n'exige pas une approbation par appel. Ne pas construire un système d'approbation manquant. |
| S5 — Révocation de A | O retire uniquement l'accès de A, sans retirer U, B ni la connexion fournisseur commune. | Depuis le contexte ouvert puis un contexte vide, A ne lit plus D1/D2; B continue de lire D1 et reste refusé sur D2. Les droits source de U restent inchangés. Un retrait global peut être noté comme alternative, jamais comme une révocation isolée réussie. |
| S6 — Preuve et bilan | Consulter les traces disponibles, puis retirer les artefacts créés pour l'essai. | Relier appel, utilisateur, agent/client, ressource, décision et résultat; noter les champs indisponibles ou limités par l'édition. Confirmer retrait des connexions et configuration temporaires, puis conservation des preuves expurgées. |

Pour S5, enregistrer l'heure de confirmation du retrait et faire des lectures
nouvelles à t=0, 5, 30, 60 et 300 secondes, jusqu'au premier refus puis un
contrôle de stabilité à 300 secondes. Vérifier B au début et à la fin. Ce sont
des points d'observation, pas une promesse de délai contractuel. Si l'accès
persiste à 300 secondes, rapporter « persiste après cinq minutes observées ».
Ne pas confondre une erreur réseau, une panne du fournisseur ou l'expiration
naturelle d'un jeton/grant avec une révocation réussie. Les droits et sessions
doivent être encore valides pendant toute cette fenêtre avant le retrait.
Les données déjà reçues ne sont pas censées disparaître de l'historique.

Une seconde exécution ciblée de S2/S3/S5 depuis un état de droits rétabli permet
de distinguer une erreur de configuration d'un comportement reproductible.
Elle reste dans la borne d'effort; sinon noter « une seule observation ».
Pour une divulgation inattendue, interrompre le cas, conserver les faits du
tenant fictif, relire la configuration et limiter la reproduction à ce périmètre.

## 6. Mesures, preuves et interprétation

Pas de score global arbitraire ni de classement fondé sur le nombre de
connecteurs. Pour chaque scénario et chaque offre, consigner :

- verdict : **observé conforme**, **écart observé**, **documenté seulement**,
  **non établi**, ou **bloqué par prérequis**;
- mode : configuration standard, fonction d'une autre édition, extension
  nécessaire, parcours alternatif non équivalent; et source de cette précision;
- couche qui prend la décision : fournisseur, passerelle, client ou modèle;
- identité réelle, portée, interventions O/U, temps actif et attente externe;
- appels effectifs, données reçues, résultat d'accès, preuve et limite.

Séparer la configuration par offre du parcours de l'employé. Compter les étapes
plutôt que d'en déduire qu'une interface est « intuitive ». Les temps d'un
opérateur déjà familier de Moraine ne permettent pas de conclure que Moraine
serait plus simple. Ne pas attribuer à la passerelle une restriction provenant
uniquement du fournisseur, ni présenter l'absence d'audit dans une offre d'essai
comme une absence dans le produit.

La future campagne créera un dossier neuf sous
`pilot-results/competitive-comparison/<date>-<run>/`, contenant :
`REPORT.md`, `matrix.csv`, plan figé, inventaire des éditions/versions,
configuration expurgée, corpus fictif, commandes ou gestes reproductibles,
transcriptions expurgées, observations de source disponibles et manifeste
des fichiers/empreintes. Pas de jeton, cookie, export de compte ou donnée réelle.
Les logs fournisseur ne sont pas présumés disponibles : une réponse brute et
une observation indépendante du tenant sont conservées quand possible; sinon
la limite de visibilité est explicite. Les exports conservés suffisent à
distinguer une vraie lecture d'un texte déjà présent dans le prompt.

Le rapport final comportera les deux candidats même si l'un est bloqué, une
ligne Moraine clairement limitée aux preuves existantes, les écarts et les
solutions alternatives documentées. Aucun compte ni service ne reste actif
pour cet essai sans accord; supprimer seulement les ressources qu'il a créées,
avec vérification de leur origine, et conserver les preuves antérieures.

## 7. Décision que les résultats permettraient de préparer

| Observation | Conséquence à discuter, sans décision automatique |
| --- | --- |
| Une offre couvre le parcours avec sa configuration documentée | La promesse générale n'est pas différenciante; examiner la réutilisation et les frictions réellement observées. |
| Le parcours exige une petite extension documentée | Comparer cette extension à une contribution Moraine ciblée avant d'imaginer un produit complet. |
| Un besoin précis reste insatisfait dans les deux configurations effectivement essayées | Formuler une hypothèse de différence, limitée aux éditions et conditions testées; vérifier ensuite si des utilisateurs rencontrent ce problème et souhaitent le résoudre. |
| Des essais sont bloqués par comptes, licences, identité ou temps | Conclure « comparaison incomplète »; présenter coût et action nécessaires pour lever le blocage. Aucune déduction sur la demande ou la faiblesse concurrentielle. |

La possibilité d'un produit commun aux particuliers et aux entreprises reste
ouverte. Cette expérience ne mesure ni volonté de payer, ni adoption, ni
confiance commerciale; elle prépare de meilleures questions pour ces recherches.

## 8. Revue indépendante et livraison de ce plan

Un autre agent, sans historique de rédaction, doit examiner une capture figée
du plan, la recherche et les sources utiles. Il cherchera les biais en faveur
de Moraine, les faux équivalents d'identité, les preuves insuffisantes, les
prérequis cachés, les limites de mandat et les conclusions commerciales abusives.
Son rapport identifiera la capture par SHA-256, donnera des constats priorisés
et distinguera un plan prêt à proposer d'un essai autorisé ou exécuté.

Les constats seront traités dans le plan maintenu et les corrections importantes
revues sur une seconde capture, en conservant les deux versions et les deux
verdicts. Contrôles de livraison : chemins et ancres des documents, empreintes
des captures, absence de secrets et `git diff --check`. Aucune suite métier
n'est nécessaire pour cette livraison documentaire. Aucun commit/push demandé.
