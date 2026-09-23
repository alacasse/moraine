# Moraine et le marché entreprise de l'accès des agents

Date : **21 septembre 2026**. Statut : **recherche exploratoire**, sans choix de
marché, d'architecture ou de fournisseur. Toutes les sources externes ci-dessous
ont été consultées à cette date. Recherche documentaire auprès des éditeurs
uniquement : **aucune offre n'a été installée ou testée**, aucun fournisseur ou
acheteur contacté. « Documenté » signifie décrit par l'éditeur, pas validé par
Moraine; « non établi » signifie que les sources examinées ne suffisent pas.

## Réponse directe

**Oui, plusieurs équivalents existent déjà pour la vision générale.** Arcade,
Workato et Obot documentent une couche centrale reliant différents clients
agents aux outils de l'entreprise, avec identité, politiques et suivi des
appels. Glean documente également une passerelle et le déploiement de sa
configuration sur les postes. Pipedream Conduit annonce très directement le
scénario envisagé, mais en accès anticipé. La promesse « l'entreprise prépare
les accès, les employés utilisent leurs assistants » n'est donc pas un espace
inoccupé. Voir leurs
[guides Arcade](https://docs.arcade.dev/en/operate/quickstart),
[Workato](https://docs.workato.com/en/mcp/mcp-gateway),
[Obot](https://docs.obot.ai/),
[Glean](https://docs.glean.com/administration/platform/mcp/external-gateway-tools)
et l'[annonce Conduit](https://pipedream.com/conduit).

Cela ne démontre ni que ces offres satisfont tous les usages, ni qu'il n'y a
plus de produit à créer. **L'occasion éventuelle se situe dans une expérience
ou un besoin insuffisamment servi**, à vérifier auprès d'utilisateurs, plutôt
que dans l'existence même d'un intermédiaire entre agents et services.

Le point de comparaison est l'hypothèse discutée : un même cœur pour
particuliers et organisations, plusieurs assistants, des accès qui survivent
aux conversations, des connecteurs préparés par l'entreprise et peu de
configuration individuelle. Moraine reste un petit pilote : sélection fixe,
droits de 30 minutes, identité configurée, fournisseur fictif et canal humain
simulé. Les preuves de deux conversations Codex réutilisant un accès ne
qualifient ni annuaire, ni plusieurs utilisateurs, ni connecteur SaaS réel,
ni déploiement d'entreprise.
[État actuel](../status.md),
[architecture](../architecture.md),
[preuve du parcours](../../pilot-results/codex-email/20260921-agent-access/REPORT.md).

## Neuf offres à comparer

Les catégories décrivent leur rapport à l'hypothèse Moraine, pas des frontières
étanches : une offre peut être concurrente comme produit et complémentaire
comme infrastructure. Les nombres de connecteurs annoncés ne sont pas utilisés
comme mesure de qualité ou de couverture effective.

| Offre et proximité | Connecteurs et clients documentés | Configuration, identité et contrôles | Conditions et limites de comparaison |
| --- | --- | --- | --- |
| **Arcade — concurrent direct** | Catalogue comprenant Jira, Confluence, Gmail et Slack; outils maison et serveurs MCP distants réunis dans une passerelle pour plusieurs clients. [Catalogue](https://docs.arcade.dev/en/home), [Atlassian](https://docs.arcade.dev/en/operate/governance/remote-mcp-servers/atlassian). | L'opérateur choisit les outils et branche l'IdP OIDC. Le sujet utilisateur doit rester stable entre sessions. Des extensions contrôlent visibilité, paramètres avant exécution et résultats après exécution. [Identité](https://docs.arcade.dev/en/operate/identity/user-sources), [contrôles](https://docs.arcade.dev/en/operate/governance/contextual-access). | Cloud et auto-hébergement Kubernetes documentés; audit administratif disponible. Recouvrement très fort. Un parcours complet de consentement personnel au périmètre métier exact n'est pas établi par ces guides. [Déploiement](https://docs.arcade.dev/en/operate/quickstart). |
| **Workato Enterprise MCP — concurrent direct, intégrateur possible** | Clients MCP externes, serveurs préconstruits, recettes métier et proxy vers d'autres serveurs; Jira et Confluence documentés. [FAQ](https://docs.workato.com/en/agentic/faqs.html), [Confluence](https://docs.workato.com/connectors/confluence.html). | SSO, groupes par serveur et outil, identité appelante dans les traces. Verified User Access conserve les connexions personnelles et exécute avec leurs droits. Les appels et changements administratifs sont journalisés. [Gateway](https://docs.workato.com/en/mcp/mcp-gateway). | Configuration dans la plateforme Workato. L'utilisateur peut encore devoir autoriser chaque application. VUA exige les types OAuth/recettes compatibles; une recette imbriquée peut utiliser le compte de service au lieu de l'identité utilisateur. Confluence MCP exige Cloud. [Limites VUA](https://docs.workato.com/en/mcp/verified-user-access). |
| **Obot — concurrent direct et base possible** | Passerelle indépendante du client/modèle, registres, serveurs hébergés ou distants et outils composites. La couverture Jira/Confluence prête à l'emploi n'a pas été établie dans cette recherche. [Vue d'ensemble](https://docs.obot.ai/). | Politiques par utilisateur/groupe; autorisation du client séparée de celle du service distant; identifiants amont conservés côté passerelle, autorisation existante réutilisable. Journaux des requêtes/réponses. [Architecture](https://docs.obot.ai/concepts/architecture/), [audit](https://docs.obot.ai/functionality/audit-logs-and-usage/). | Docker/Kubernetes documentés. Édition gratuite limitée à 100 utilisateurs et appareils; SSO Entra/Okta/Auth0 via inscription Community ou licence Enterprise. Version documentaire v0.25.0; gestion des appareils indiquée bêta. [Éditions](https://docs.obot.ai/enterprise/overview/), [hébergement](https://docs.obot.ai/concepts/mcp-gateway/). |
| **Pipedream Connect / Conduit — brique et concurrent direct émergent** | Connect fournit outils/API/MCP et authentification par utilisateur; Confluence offre lecture, création, modification et suppression. Conduit vise les assistants MCP existants et les services internes. [Connect](https://mcp.pipedream.com/developers), [Confluence](https://mcp.pipedream.com/app/confluence). | Conduit annonce SSO OIDC, affectation des groupes depuis l'IdP, droits par connecteur/outil et utilisateur/groupe, audit et changements d'accès immédiats. | **Conduit : accès anticipé**, cloud ou Docker annoncés; pas assimilé à un déploiement éprouvé. Granularité par document, consentements résiduels et conditions commerciales restent à vérifier. Connect est une infrastructure distincte à intégrer. [Offre Conduit](https://pipedream.com/conduit). |
| **Composio — concurrent partiel et fournisseur de connecteurs** | Sessions exposées par MCP et plugins pour agents existants; Jira et Confluence, avec opérations de lecture/écriture. [Jira](https://docs.composio.dev/kb/guide/toolkits-jira), [Confluence](https://docs.composio.dev/toolkits/confluence), [plugins](https://docs.composio.dev/docs/agent-plugins). | Connexions rattachées au projet/utilisateur, réutilisables dans d'autres sessions; comptes épinglés et listes d'outils autorisés. Le guide B2B distingue comptes individuels et compte d'intégration d'organisation. [Sessions](https://docs.composio.dev/kb/guide/mcp-tool-router-sessions), [B2B](https://docs.composio.dev/docs/b2b-agents). | L'application cliente reste responsable des droits d'appartenance à l'organisation; connexions partagées indiquées expérimentales. Enhanced Control dépend de l'elicitation MCP du client. Un produit complet d'administration de parc n'est pas établi; l'offre « For You » recouvre déjà l'usage personnel multi-agent. [Documentation](https://docs.composio.dev/docs). |
| **Glean — suite substitutive et concurrent direct via MCP** | Connecteurs Jira/Confluence et autres sources avec indexation des données et permissions. La passerelle expose aussi des outils externes vers des clients tels que Cursor et Claude Code. [Connecteurs](https://docs.glean.com/connectors), [Gateway](https://docs.glean.com/administration/platform/mcp/external-gateway-tools). | Administrateur, SSO, outils par serveur et accès par groupe/rôle; déploiement MDM pour éviter la configuration manuelle des postes. L'employé s'authentifie encore. [Déploiement MDM](https://docs.glean.com/administration/platform/mcp/mdm-mcp). | Nécessite une instance Glean. Distinguer recherche indexée, outils externes et agents Glean exportés : ces derniers ne peuvent contenir ni écriture ni attente humaine, y compris dans leurs sous-agents. Cela ne prouve pas que tous les outils de la passerelle sont en lecture seule. [Contraintes](https://docs.glean.com/administration/platform/mcp/agents-as-tools). |
| **Atlassian Rovo / Atlassian MCP — substitut natif et connecteur possible** | Accès Jira, Confluence et Compass depuis différents clients MCP avec droits Atlassian existants. [Contrôles](https://support.atlassian.com/security-and-access-policies/docs/control-atlassian-rovo-mcp-server-settings/). | L'administrateur contrôle domaines clients et permissions lecture/écriture/recherche; journal des outils et utilisateurs. Guard ajoute des blocages de lecture par espaces/classifications. [Permissions](https://support.atlassian.com/security-and-access-policies/docs/Configure-Atlassian-Rovo-MCP-server-permission/), [audit](https://support.atlassian.com/security-and-access-policies/docs/monitor-atlassian-rovo-mcp-server-activity/). | Très pertinent si le besoin est d'abord Jira/Confluence. Les politiques de protection MCP étudiées couvrent OAuth, pas les jetons API ni les serveurs MCP personnalisés. Ce n'est pas une politique universelle couvrant tous les fournisseurs. [Périmètre Guard](https://support.atlassian.com/security-and-access-policies/docs/prevent-atlassian-rovo-mcp-server-access/). |
| **Auth0 for AI Agents — brique complémentaire et recouvrement fonctionnel** | Authentification, coffre/échange de jetons pour API tierces et intégrations SDK. Un catalogue d'actions Jira/Confluence équivalent à Arcade n'est pas établi. [Vue d'ensemble](https://auth0.com/docs/get-started/auth0-for-ai-agents). | Token Vault porte les connexions; FGA les contrôles fins; CIBA/RAR une approbation asynchrone sur canal distinct, avec Guardian ou email selon l'offre. | Service à intégrer : l'application construit encore l'expérience et l'exécution métier. CIBA exige Enterprise ou un complément et **ne conserve pas de grant de consentement durable** pour les autres flows. CIBA seul ne remplace donc pas la continuité d'accès de Moraine. [Contrat CIBA](https://auth0.com/docs/get-started/authentication-and-authorization-flow/client-initiated-backchannel-authentication-flow). |
| **Microsoft Entra Agent ID / Agent 365 — socle d'identité et suite concurrente** | Identités d'agents distinctes, accès délégué utilisateur, agents externes intégrables; outils Microsoft 365 et serveurs MCP apportés par l'entreprise. Jira/Confluence natifs dans ce chemin : non établis. [Agents externes](https://learn.microsoft.com/en-us/microsoft-agent-365/connect-existing-agents), [OBO](https://learn.microsoft.com/en-us/entra/agent-id/agent-on-behalf-of-oauth-flow). | Sponsors, droits préétablis ou demandés via access packages, registre, approbation/blocage d'outils et supervision. [Administration](https://learn.microsoft.com/en-us/entra/agent-id/manage-agent-identities-admin), [outils](https://learn.microsoft.com/en-us/microsoft-365/admin/manage/manage-tools-for-agent?view=o365-worldwide). | Agent ID et Agent 365 sont indiqués GA; Agent 365 commercial depuis mai 2026, sous licence. L'appel des serveurs BYO depuis certaines surfaces reste indiqué en preview : ne pas étendre le statut GA à tout. [Disponibilité](https://learn.microsoft.com/en-us/microsoft-agent-365/overview), [Agent ID](https://learn.microsoft.com/en-us/entra/agent-id/whats-new-agent-id). |

## Ce qui compte dans ces recouvrements

**La neutralité envers les assistants est déjà proposée.** Glean n'est plus à
classer seulement comme un assistant fermé : son guide Gateway du 9 septembre
2026 décrit l'exposition d'outils externes. Son guide MDM du 27 août inclut Codex,
Cursor et Gemini CLI. Arcade décrit une configuration opérateur complète dans
un guide du 16 septembre. Ce sont des modes opératoires, pas uniquement des
slogans; leur facilité réelle reste à mesurer.
[Glean Gateway](https://docs.glean.com/administration/platform/mcp/external-gateway-tools),
[MDM](https://docs.glean.com/administration/platform/mcp/mdm-mcp),
[Arcade](https://docs.arcade.dev/en/operate/quickstart).

**« Préparer les accès » recouvre plusieurs gestes.** Préinstaller une adresse
MCP, affecter un groupe, autoriser un outil et connecter le compte source ne
sont pas interchangeables. Workato décrit encore un consentement auprès de
chaque application quand la connexion manque. Glean automatise la configuration
du poste, mais conserve l'authentification de l'employé. L'objectif sans
configuration spéciale est donc crédible; **zéro intervention pour tout
fournisseur** n'est pas démontré.
[Workato VUA](https://docs.workato.com/en/mcp/verified-user-access),
[Glean MDM](https://docs.glean.com/administration/platform/mcp/mdm-mcp).

**La continuité entre conversations est une propriété attendue de cette
catégorie.** Composio documente explicitement qu'une connexion appartient au
projet/utilisateur et peut être retrouvée dans une session ultérieure. Cela
confirme la pertinence du pilote Moraine, sans en faire une différence
commerciale. En revanche, distinguer plusieurs agents d'une même personne et
leurs délégations doit être testé séparément : un `user_id`, un client OAuth
et une identité d'agent ne désignent pas nécessairement la même chose.
[Composio sessions](https://docs.composio.dev/kb/guide/mcp-tool-router-sessions),
[identité agent Microsoft](https://learn.microsoft.com/en-us/entra/agent-id/agent-identities).

**Lecture, écriture, accord et révocation demandent une comparaison précise.**
Bloquer un outil n'est pas limiter sa lecture à un dossier; consentir OAuth
n'est pas approuver un message exact. Atlassian apporte toutefois déjà des
restrictions de contenu par espace, et Auth0 un canal d'approbation distinct.
Il serait donc injustifié de présenter la granularité ou l'approbation humaine
comme absentes du marché.
[Atlassian Guard](https://support.atlassian.com/security-and-access-policies/docs/prevent-atlassian-rovo-mcp-server-access/),
[Auth0 CIBA](https://auth0.com/docs/get-started/authentication-and-authorization-flow/client-initiated-backchannel-authentication-flow).

Les mécanismes de retrait diffèrent : Workato décrit la déconnexion immédiate
des clients lors de révocation du jeton; Conduit annonce des changements
d'accès immédiats; Auth0 décrit l'invalidation de futurs échanges après
révocation. Aucun de ces textes ne prouve le rappel des données déjà reçues,
ni un délai universel de retrait des droits source dans tous les connecteurs.
La latence réelle de révocation et le comportement des copies sont des points
de comparaison à tester, y compris pour Moraine.
[Workato](https://docs.workato.com/en/mcp/mcp-gateway),
[Conduit](https://pipedream.com/conduit),
[Token Vault](https://auth0.com/blog/auth0-token-vault-secure-token-exchange-for-ai-agents/).

## Ce qui paraît déjà couvert, ce qui reste hypothétique

Une adresse MCP centrale, OAuth géré, connexions persistantes, catalogue
d'outils, SSO, politiques de groupe, contrôle lecture/écriture et audit sont
déjà des caractéristiques documentées. **Construire seulement cet assemblage
réduit fortement l'intérêt d'une nouvelle offre générale**, particulièrement
face à Arcade, Workato, Obot et Glean. Conduit renforce cette pression, avec
une maturité à vérifier. Pour un besoin limité à Jira/Confluence, l'offre
native Atlassian pourrait suffire; c'est une hypothèse d'achat à confronter
aux usages, pas une recommandation de migration.

Restent des différences possibles, **non prouvées** : une personne comprend
réellement ce que chaque agent peut voir; déléguer un dossier ou une tâche est
simple; les mêmes gestes fonctionnent en contexte personnel et administré;
la réduction ou suspension d'un accès oublié est compréhensible; une action
approuvée correspond à un contenu exact, avec résultat incertain correctement
expliqué. Moraine possède des mécanismes pilotes sur certains de ces points,
mais pas encore une expérience qualifiée ni un avantage comparatif mesuré.
[Exploration produit](delegation-ux-multi-provider.md),
[contrat du pilote](../pilot/interface.md).

La combinaison particuliers/entreprises demeure possible, mais ne constitue
pas à elle seule une différence : Composio documente déjà les deux modèles
de connexion. Son économie, son support et la séparation des données
personnelles/professionnelles restent à découvrir pour Moraine.
[Modèles Composio](https://docs.composio.dev/docs/b2b-agents).

## Trois hypothèses de positionnement à départager

Ces hypothèses sont des propositions de recherche commerciale, sans priorité
acceptée ni mandat pour contacter des entreprises ou développer un produit.

| Hypothèse | Bénéfice possible et articulation avec les offres | Obstacle principal | Test commercial proposé |
| --- | --- | --- | --- |
| **Gestion des délégations compréhensible par la personne**, utilisable seule puis avec une organisation | Donner une vue claire par agent, ressource et activité; faciliter retrait, extension et accès oubliés. Employer Composio/Pipedream pour certains connecteurs et Auth0 pour l'identité serait envisageable. | Composio For You et les interfaces natives occupent déjà ce terrain. L'utilisateur paiera-t-il pour cette maîtrise plutôt que pour l'assistant lui-même ? Les contraintes d'entreprise pourraient compliquer l'expérience personnelle. | Faire raconter puis comparer le même parcours à des particuliers avancés et employés de petites équipes : connecter deux assistants, limiter un dossier, changer d'assistant, retirer l'accès. Mesurer les incompréhensions, le temps et une intention d'achat explicite face à une solution existante. |
| **Mise en service administrée pour petites entreprises**, avec un périmètre de services limité | Une offre exploitée, facile à installer et accompagner, évitant que chaque employé configure ses outils. Moraine pourrait intégrer une passerelle existante plutôt que reconstruire le catalogue. | Concurrence directe Arcade, Obot, Workato, Glean et Conduit. « Plus simple » et « moins cher » ne sont pas encore démontrés; support, maintenance et confiance peuvent absorber la marge. | Avec quelques responsables IT, comparer un déploiement concret déjà disponible à une proposition Moraine : assistants acceptés, temps administrateur, gestes employés, coût total et responsable du budget. Écarter l'hypothèse si l'existant répond au besoin sans friction coûteuse. |
| **Délégations et preuves d'exécution pour un usage métier précis**, intégrées aux plateformes en place | Ajouter un parcours d'autorisation et un reçu compréhensible pour un acte sensible : documents sélectionnés, action exacte, état persistant, retrait et incertitude. S'insérer comme outil MCP ou extension derrière Arcade, Workato, Obot ou Agent 365 est une possibilité technique à vérifier. | Un client peut déjà obtenir le résultat par recette Workato, hooks Arcade ou Auth0. Doubler les consoles de politiques et l'audit peut dégrader le produit. La valeur vient du besoin métier résolu, pas d'un nonce ou d'un moteur de règles. | Demander à des équipes de montrer une opération actuellement bloquée ou coûteuse. Vérifier si leur plateforme sait déjà la traiter; proposer ensuite une démonstration du résultat métier et rechercher un engagement pilote avec budget identifié. |

Les points d'intégration ne sont pas inventés : Arcade expose des hooks de
contrôle; Workato et Obot des proxys MCP; Microsoft accepte l'enregistrement de
serveurs MCP externes. **La compatibilité de Moraine avec ces surfaces n'a pas
été testée**, et une composition ne préserve pas automatiquement identité,
périmètre ou preuve d'approbation.
[Arcade](https://docs.arcade.dev/en/operate/governance/contextual-access),
[Workato](https://docs.workato.com/en/mcp/mcp-gateway),
[Obot](https://docs.obot.ai/concepts/mcp-gateway/),
[Microsoft BYO](https://learn.microsoft.com/en-us/microsoft-365/admin/manage/manage-tools-for-agent?view=o365-worldwide).

## Inconnues commerciales utiles pour la suite

- **Quel acheteur et quelle douleur ?** IT qui déploie, sécurité qui bloque,
  équipe métier qui attend, ou personne qui veut garder la main ? Le même
  mécanisme peut correspondre à des budgets et critères d'achat différents.
- **Que coûte le problème aujourd'hui ?** Temps de configuration, accès trop
  larges, maintenance des connecteurs, outil interdit, tâche manuelle : obtenir
  des exemples vécus avant de supposer un marché.
- **Pourquoi ajouter Moraine quand une suite est déjà payée ?** Identifier
  une lacune concrète qui justifie une dépendance et une console de plus.
- **Quelle promesse est suffisamment précise pour être achetée ?** Accès prêt
  pour les employés, maîtrise personnelle ou opération métier débloquée; la
  « gouvernance des agents » seule reste trop large pour départager les offres.
- **Un cœur commun suffit-il commercialement ?** Les particuliers et
  entreprises peuvent partager le mécanisme tout en demandant des offres,
  contrats, canaux de distribution et niveaux de service distincts.

Cette recherche établit **une concurrence réelle et des possibilités de
composition**, pas une taille de marché, une volonté de payer ou un segment
retenu. Les contrats, résidence des données, coûts complets et garanties
opérationnelles n'ont pas été comparés. Les conditions publiques citées
servent à signaler des limites concrètes; elles ne forment pas un devis.
La prochaine connaissance manquante est surtout la réaction d'acheteurs et
d'utilisateurs à ces alternatives sur un usage précis.
