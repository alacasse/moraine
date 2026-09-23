# Workato — fiche préalable à l'accès

Date de consultation des sources : **21 septembre 2026**. Statut :
**documentaire uniquement; aucun essai produit**. Cette fiche prépare le
[plan de comparaison](../../../docs/plans/agent-access-competitive-comparison.md)
et précise la [note de prérequis](../../../docs/research/agent-access-comparison-prerequisites.md).
Aucun compte, connexion OAuth, installation, contact fournisseur ou achat effectué.

**Conclusion :** le chemin Confluence sous l'identité de U est documenté.
L'édition effectivement accessible, les scopes minimaux du connecteur et une
délégation serveur distincte pour A/B restent à établir avant leurs scénarios.
Ces inconnues ne prouvent pas l'absence des fonctions.

## Établi documentaire et conditions d'accès

| Sujet | Établi documentaire | Inconnu ou condition à lever |
| --- | --- | --- |
| Entrée gratuite | Free est annoncé à 0 $/mois, sans carte, avec 50 000 crédits accordés une fois et Enterprise MCP inclus. [Offre Free][free] | Date d'expiration des crédits et durée garantie du compte Free non trouvées. « Accordés une fois » ne signifie pas crédits permanents. Aucun compte disponible n'a été vérifié. |
| Édition | La page commerciale distingue Pro à 100 $/mois et Enterprise sur devis. La documentation self-service annonce aussi Pro dès 75 $/mois pour 2 500 crédits; 100 $ correspond à 3 500 crédits. [Free][free], [self-service][pricing] | La documentation décrit Free/Pro comme ayant les mêmes capacités, alors que la page commerciale réserve des contrôles supplémentaires à Pro/Enterprise. Aucune de ces pages ne garantit explicitement tout le lot Identity + VUA + groupes/outils + journaux requis dans Free. |
| Fin et consommation | Free est le choix initial documenté; Pro exige une souscription et des informations de paiement. Les crédits Pro inutilisés expirent mensuellement. [Self-service][pricing] | Ne pas appliquer cette expiration Pro à Free. Coût de la campagne et consommation par outil non mesurés. Aucun abonnement n'est autorisé par cette fiche. |
| Identité de U | Workato Identity gère utilisateurs/groupes manuels ou synchronisés depuis un IdP, ainsi que l'authentification par mot de passe ou SAML. L'identité est transmise dans un JWT signé. [Identity][identity] | Édition et activation dans le futur workspace. Le guide VUA commence par SAML; la documentation Identity et Gateway décrit aussi les comptes locaux : un IdP externe n'est donc pas établi comme prérequis universel. [Configuration VUA][vua-config], [Gateway][gateway] |
| Autorisation MCP | L'accès serveur dépend de groupes utilisateurs; les sous-groupes limitent les outils. Même O doit être ajouté à un groupe pour utiliser MCP; administrer le workspace ne donne pas automatiquement accès au serveur. [Gateway][gateway] | Une règle par utilisateur/groupe/outils ne démontre pas une règle par couple U–agent ni une restriction aux pages D1/D2. |
| Confluence | Le serveur préconstruit propose **User's connection**, avec OAuth authorization code; les outils incluent recherche, page, hiérarchie et pièces jointes. [Serveur Confluence][confluence-mcp] | Compatibilité effective, outils réellement exposés et recettes créées à capturer dans le tenant autorisé. |
| VUA | L'appel utilise la connexion de l'utilisateur; si elle manque ou expire, le parcours demande authentification puis consentement fournisseur. Les connexions sont conservées sur le profil utilisateur. Les jetons MCP ne conviennent pas à VUA. [VUA][vua] | Nombre de consentements pour A/B, réutilisation exacte de la connexion, persistance et rafraîchissement non observés. |
| Limite VUA | Les recettes imbriquées peuvent revenir au compte de service; VUA reste au premier niveau du parent exposé. [VUA][vua] | Inspecter le montage préconstruit avant de l'utiliser; éviter les recettes imbriquées dans cet essai. |

## OAuth Confluence et configuration prévue

Les paramètres ci-dessous sont **à configurer après autorisation**, sans valeur
de compte ou secret existant présumé.

| Paramètre | Valeur prévue ou condition |
| --- | --- |
| Workspace / projet | Workspace d'essai à désigner; projet proposé `moraine-access-comparison-20260921`. O administrateur; U utilisateur ordinaire distinct. Édition et région à enregistrer. |
| Méthode MCP | Workato Identity; U ajouté au groupe d'essai. Deux configurations client isolées A/B; aucune identité agent ne sera déduite de leurs noms. [Méthodes d'accès][access] |
| Serveur / outils | Confluence préconstruit; commencer par `search_pages`, `get_page`, `get_page_hierarchy`, `get_attachments`; retirer les outils d'écriture de l'exposition. Le retrait d'outils ne démontre pas une restriction de pages. [Serveur][confluence-mcp] |
| Source | Confluence Cloud d'essai à désigner, corpus fictif D1–D4 et droits initiaux du plan. Ne connecter aucun tenant réel. |
| Connexion | `User's connection`; Cloud; OAuth 2.0 authorization code; sous-domaine du tenant; client ID et secret privés. U choisit le site puis consent. [Serveur][confluence-mcp] |
| Application Atlassian | Application OAuth 2.0 à créer; callback documenté `https://www.workato.com/oauth/callback`. Les réglages avancés proposent Classic scopes ou Granular scopes. [Connecteur Confluence][confluence-connector] |
| Secrets / preuve | Secrets et connexions brutes hors Git; conserver mode, scopes effectifs, IDs expurgés, versions des recettes/outils, approbations et résultats. Aucun appel nécessaire pour cette fiche. |

**Scopes : la configuration publiée est plus large que la lecture.** Le guide
du connecteur prescrit les scopes ci-dessous, sans isoler le minimum d'une
connexion limitée aux lectures :

- Lecture : `read:confluence-groups`, `read:confluence-content.all`,
  `read:confluence-content.permission`, `read:confluence-content.summary`,
  `read:confluence-props`, `read:confluence-space.summary`, `read:confluence-user`,
  `read:page:confluence`, `readonly:content.attachment:confluence`,
  `search:confluence`.
- Gestion/écriture également prescrites : `manage:confluence-configuration`,
  `write:confluence-content`, `write:confluence-file`, `write:confluence-groups`,
  `write:confluence-space`. [Connecteur Confluence][confluence-connector]

Atlassian documente `read:page:confluence` pour lire une page par ID en REST v2,
et `search:confluence` pour la recherche REST v1 (alternative granulaire :
`read:content-details:confluence`). Ce sont des exigences des endpoints,
**pas la preuve que ces seuls scopes suffisent au connecteur Workato**.
Les endpoints effectivement utilisés pour hiérarchie, pièces jointes,
initialisation et vérification de connexion restent à identifier.
[Page v2][atlassian-page], [Search v1][atlassian-search]

Un sous-ensemble de lecture constitue une **configuration candidate à qualifier**.
Le besoin technique obligatoire des cinq scopes de gestion/écriture n'est pas
établi. S'ils sont exigés par la connexion réelle, arrêter avant consentement
et faire trancher leur octroi; le mandat de lecture ne vaut pas autorisation
implicite de cet élargissement. Les scopes ne remplacent pas les permissions
Confluence de U. [Définition Atlassian des scopes][atlassian-scopes]

## Identités A/B, révocation et preuves

| Point à démontrer | Documenté | Verdict préalable / contrôle nécessaire |
| --- | --- | --- |
| A et B au nom du même U | Workato documente l'authentification OAuth et l'accès par groupes; l'enregistrement dynamique de clients MCP est mentionné. [Méthodes][access], [configuration MCP][mcp-config] | **Non établi.** Identifier un principal ou grant A/B authentifié utilisé par une politique serveur. Deux clients enregistrés ou deux URL seuls ne prouvent pas cette politique. |
| Matrice D1–D4 | VUA applique les droits fournisseur de U; RBAC restreint les outils. [VUA][vua], [Gateway][gateway] | **Non établi** pour la restriction de contenu propre à A/B. Trouver le réglage serveur qui refuse D3 aux deux et D2 à B sans changer les droits source de U, puis tester ID, recherche et métadonnées. |
| Révocation isolée | Supprimer/renouveler un jeton MCP retire les clients qui l'utilisent. [Méthodes][access] | Ce chemin est incompatible avec le VUA retenu. Révocation d'un client/grant OAuth A sans affecter B : **non établie** dans les sources consultées. |
| Connexions persistantes | Les connexions créées à l'exécution persistent. La console permet de supprimer une connexion enfant, ce qui impose une nouvelle authentification; supprimer le parent ne supprime pas les enfants. [Runtime user connections][runtime] | Une connexion propre à A est une piste standard à examiner, pas une séparation prouvée. Vérifier sa clé de rattachement et si B partage la connexion; empêcher la confusion avec un simple consentement refait. |
| Journaux d'appel | Gateway décrit utilisateur, méthode d'authentification, IP, user-agent, outil, entrées/sorties, durée et succès/échec; les jobs décrivent les étapes. [Gateway][gateway] | Identifiant authentifié A/B, décision d'autorisation explicite, couverture des refus et jointure avec la ressource : **à vérifier**, sans prendre user-agent pour identité. |
| Disponibilité des traces | Le Logging Service dépend du contrat et du privilège Logs; la page fournit aussi une entrée self-service. Rétention maximale annoncée : 30 jours ou un million d'entrées; données tronquées à 10 Ko par entrée. [Logging Service][logging] | Inclusion réelle dans Free et export exploitable inconnus. Conserver réponses expurgées hors des seuls logs; ne pas conclure à l'absence d'audit du produit si le compte n'y accède pas. |

La durée de vie documentée du jeton d'accès Workato Identity est une heure;
les refresh tokens n'ont pas de quota de durée annoncé. Pour S5, vérifier la
validité effective avant retrait et distinguer révocation et expiration.
[Identity][identity]

## Décisions et accès encore nécessaires

1. Désigner ou autoriser le workspace Free, les comptes O/U, le tenant Confluence
   et l'application OAuth; confirmer conditions d'expiration et fonctions
   effectivement accessibles. Aucune utilisation de compte déjà connecté
   n'est présumée autorisée.
2. Autoriser l'upload du corpus fictif et le consentement de U avec la liste
   finale de scopes. Choisir un IdP seulement si le compte retenu l'exige.
3. Désigner le client MCP, son modèle éventuel et le budget d'appels; autoriser
   les configurations temporaires. Aucun montant payant n'est présumé accepté.
4. Avant S2/S5, disposer d'un réglage serveur ou d'une preuve documentaire
   vérifiable reliant A/B à leurs délégations et à l'objet révoqué. À défaut,
   consigner ces cas comme non établis et poursuivre uniquement les cas
   indépendants autorisés.

**Réutilisation candidate :** serveur Confluence, Identity, VUA, groupes et
traces constituent les composants documentés à essayer tels quels. Une recette
filtrant les pages selon une identité agent vérifiée, une politique externe ou
un parcours de demande/approbation seraient des **extensions hypothétiques**;
leur nécessité, faisabilité et effort ne sont pas mesurés. Elles ne font pas
partie de cette campagne initiale. Aucun écart commercial ou besoin client
n'est déduit de la recherche.

**Versions :** documentation publique consultée à la date ci-dessus; OAuth 2.0
et endpoints Atlassian v1/v2 identifiés. Build SaaS Workato, version du template
Confluence, révisions des recettes/connecteurs, protocole MCP négocié et version
du client : **inconnus, aucun déploiement observé**. La page Atlassian des scopes
affiche une mise à jour au 18 septembre 2026; plusieurs pages Workato affichent
un champ de mise à jour vide. Une date de consultation n'est pas une version.

**Borne de recherche :** début relevé à 17:44:24 UTC le 21 septembre 2026;
fin à 17:46:41 UTC, soit 2 min 17 s, lectures et rédaction comprises. Recherche publique
officielle bornée à 15 minutes, sans réponse commerciale ni accès authentifié.
Requêtes ciblées sur coût/expiration, Identity/VUA, scopes, clients/révocation
et audit. Les pages Markdown Workato non accessibles ont été remplacées par
leurs pages HTML officielles. Les inconnues ci-dessus subsistent; aucune
recherche exhaustive de toutes les éditions n'est revendiquée.

**Vérifications locales :** deux liens vers des fichiers existants, 15 références
URL définies, aucune référence manquante ni espace final. `git diff --check`
ne signale rien; ce fichier nouveau a aussi été contrôlé directement en Python.
Les sources liées ont été consultées le 21 septembre 2026.

[free]: https://www.workato.com/free
[pricing]: https://docs.workato.com/en/pricing/self-service/self-service.html
[identity]: https://docs.workato.com/en/workato-identity
[vua-config]: https://docs.workato.com/en/mcp/verified-user-access-configuration
[gateway]: https://docs.workato.com/en/mcp/mcp-gateway
[confluence-mcp]: https://docs.workato.com/en/mcp/prebuilt-mcps/confluence-mcp-server
[confluence-connector]: https://docs.workato.com/en/connectors/confluence.html
[vua]: https://docs.workato.com/en/mcp/verified-user-access
[access]: https://docs.workato.com/mcp/mcp-authentication
[mcp-config]: https://docs.workato.com/en/mcp/mcp-server-access-and-configuration
[runtime]: https://docs.workato.com/en/features/runtime-user-connections
[logging]: https://docs.workato.com/en/features/logging-service
[atlassian-page]: https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-page/#api-pages-id-get
[atlassian-search]: https://developer.atlassian.com/cloud/confluence/rest/v1/api-group-search/
[atlassian-scopes]: https://developer.atlassian.com/cloud/confluence/scopes-for-oauth-2-3LO-and-forge-apps/
