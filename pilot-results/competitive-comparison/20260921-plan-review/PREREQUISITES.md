# Prérequis d'un essai comparatif Arcade / Workato

Date : **21 septembre 2026**. Statut : **préparation documentaire**, complément
de l'[étude de marché](enterprise-agent-access-market.md). Huit sources
officielles consultées à cette date, sans compte créé, installation, contact
commercial ou appel payant. Les disponibilités ci-dessous sont documentées
publiquement; aucune fonctionnalité n'a été essayée.

## Avis pour le plan

**Arcade et Workato sont deux comparateurs pertinents, mais un essai complet
n'est pas encore garanti exécutable.** Les deux proposent une entrée gratuite.
Les conditions d'accès aux fonctions d'entreprise et surtout la restriction
de deux agents du même employé restent à établir. Prévoir un contrôle de ces
conditions avant le benchmark, avec résultat « non accessible » ou « non
établi », sans remplacer discrètement le produit ni abaisser l'exigence.

## Accès et coûts publiquement vérifiés

| Point | Arcade | Workato |
| --- | --- | --- |
| Entrée self-service | Offre Free sans carte : 2 000 événements d'authentification et 2 000 appels d'outils par mois, cloud géré. | Offre Free sans carte, 50 000 crédits non renouvelables; « Enterprise MCP & AI agents » figure dans les inclusions. |
| Niveau supérieur | Team à 25 $/mois plus usage. Enterprise sur devis; SSO, RBAC, audit et registre privé y sont explicitement listés. | Pro à 100 $/mois avec certains contrôles d'accès; Enterprise sur devis avec sécurité/gouvernance étendues. |
| Condition non résolue | Ne pas déduire que User Sources/OIDC, contrôles requis et audit seront utilisables en Free. La matrice ne précise pas tous les droits d'essai. | L'inclusion générale de MCP ne prouve pas que Workato Identity, SSO, VUA et tous les contrôles requis sont activés dans le compte gratuit. |

Sources : [tarifs Arcade](https://www.arcade.dev/pricing/) et
[offre gratuite Workato](https://www.workato.com/free).
Ces prix ne comprennent ni un abonnement client agent, ni Confluence, ni un
éventuel IdP; ce ne sont pas des budgets autorisés.

## Confluence Cloud : parcours et gestes incompressibles

**Arcade.** Le toolkit Confluence documente lecture, écriture, recherche et
identification de l'utilisateur via OAuth Atlassian. Toutefois, Arcade indique
ne pas fournir d'Auth Provider Atlassian par défaut : il faut créer une
application OAuth Atlassian, enregistrer le callback, choisir les scopes et
configurer son client ID/secret dans Arcade. L'utilisateur doit ensuite
effectuer l'autorisation navigateur. La configuration fournisseur n'est donc
pas supprimée par la présence du toolkit.
[Toolkit](https://docs.arcade.dev/en/resources/integrations/productivity/confluence),
[configuration Atlassian](https://docs.arcade.dev/en/references/auth-providers/atlassian).

L'opérateur prépare les outils de chaque passerelle et son authentification.
Arcade Auth identifie des membres du projet; User Source identifie l'employé
auprès de son IdP OIDC. Le mode Headers accepte un ID utilisateur transmis par
le client : il ne démontre pas, seul, une authentification d'employé indépendante.
L'option de suppression de l'écran de consentement pour certains clients
concerne la passerelle, sans preuve qu'elle supprime l'accord Atlassian.
[Modes de passerelle](https://docs.arcade.dev/en/operate/governance/mcp-gateways).

**Workato.** L'opérateur installe le serveur Confluence et choisit **User's
connection**, plutôt que la connexion du constructeur. Ce mode exige OAuth
authorization code : application Atlassian, callback et scopes sont à
préparer. Le guide décrit ensuite l'authentification et le choix du site par
l'utilisateur. Un compte de service partagé ne serait pas un résultat
équivalent.
[Serveur Confluence](https://docs.workato.com/en/mcp/prebuilt-mcps/confluence-mcp-server).

L'administrateur doit aussi ajouter l'employé à un groupe autorisé au serveur,
même s'il est lui-même administrateur. VUA requiert Workato Identity; une
connexion manquante ou expirée déclenche une authentification fournisseur.
Les jetons API ne supportent pas VUA. Éviter les recettes imbriquées pour
l'essai : la documentation signale un retour au compte de service dans ce cas.
[Gateway](https://docs.workato.com/en/mcp/mcp-gateway),
[VUA](https://docs.workato.com/en/mcp/verified-user-access).

Il faut donc disposer d'un site Confluence Cloud autorisé pour l'essai, d'un
opérateur habilité à configurer ces intégrations, d'une identité employé et
de clients MCP compatibles. L'employé conserve au minimum les gestes
d'authentification et de consentement exigés par le parcours retenu. Leurs
nombres et leur répétition entre clients sont des mesures, pas des promesses.

## Deux agents, même employé : inconnue décisive

Arcade documente une sélection d'outils par passerelle; Workato des droits
par serveur, outil et groupe utilisateur. **Ces documents ne démontrent pas
une règle distincte par couple employé–agent**, ni la révocation d'une seule
délégation OAuth tout en conservant l'autre. Deux URL avec des outils
différents prouvent une configuration différente, pas nécessairement que
l'agent A ne peut pas obtenir l'accès de B.
[Arcade](https://docs.arcade.dev/en/operate/governance/mcp-gateways),
[Workato](https://docs.workato.com/en/mcp/mcp-gateway).

Workato garantit le retrait des clients utilisant un jeton révoqué, mais
ce mécanisme ne résout pas le scénario VUA, incompatible avec ces jetons.
Pour les deux offres, identifier l'objet exact retiré — client OAuth, grant,
connexion fournisseur, groupe ou passerelle — et son rayon d'effet reste
un préalable. **Non établi n'est pas synonyme d'impossible.**

## Proposition de protocole, non exécutée

Le [plan de comparaison](../plans/agent-access-competitive-comparison.md)
fixe le protocole à soumettre à revue; les étapes ci-dessous en sont la base.

1. Confirmer dans l'édition disponible les fonctions requises et leur coût,
   puis conserver les paramètres, versions et modes d'authentification. Une
   limite commerciale produit un résultat distinct d'une limite fonctionnelle.
2. Utiliser une seule identité employé ayant accès à trois pages fictives
   D1, D2 et D3, plus D4 réservée à l'administrateur. Prévoir deux agents
   authentifiés : A peut lire D1/D2; B peut lire D1; aucun ne doit lire D3/D4.
   Deux noms ou conversations ne constituent pas deux identités prouvées.
3. Vérifier les refus par lecture directe d'ID et recherche, puis retrouver
   les droits dans de nouvelles conversations. Distinguer restriction d'outil,
   restriction de contenu et refus hérité des droits source.
4. Retirer seulement l'accès de A; vérifier que B fonctionne encore et que
   l'employé conserve ses droits Confluence. Tester un ancien jeton et une
   nouvelle session, sans remettre A en état par une réautorisation cachée.
5. Compter interventions employé/admin, développements spécifiques et appels
   facturables. Un paramètre fourni par l'agent ou une URL cachée ne suffit
   pas comme contrôle d'autorisation.

**Conserver les deux choix.** Arcade évalue un runtime spécialisé; Workato une
plateforme d'intégration administrée. Si un accès manque, documenter ce blocage
et ce qui reste comparable. Obot pourrait faire l'objet d'un autre essai
explicitement décidé; il ne remplace pas automatiquement un candidat difficile
à tester.
