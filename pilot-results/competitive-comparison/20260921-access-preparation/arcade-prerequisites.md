# Arcade — fiche de préparation

Date : **21 septembre 2026**. Statut : **documenté seulement; aucun essai produit**.
Recherche publique et rédaction : **17:44:15–17:47:17 UTC** (3 min 02 s écoulées,
sans configuration ni attente d'accès externe). Comptes, console authentifiée,
OAuth, installations, appels de modèles et contacts commerciaux : **aucun**.
Cette fiche applique le [plan](../../../docs/plans/agent-access-competitive-comparison.md)
et complète la [note préalable](../../../docs/research/agent-access-comparison-prerequisites.md).

**Le parcours complet reste bloqué par des accès non désignés et non autorisés.**
La documentation établit un socle réutilisable — identité utilisateur, passerelles,
coffre OAuth et traces — mais ne démontre pas les restrictions D1/D2 par agent
du même U ni leur révocation sélective. Ce résultat ne démontre aucune faiblesse
du produit, ni une différence commerciale pour Moraine.

## Accès, édition et coût

| Objet | Établi documentaire au 21 septembre 2026 | Inconnu à lever |
| --- | --- | --- |
| Arcade Cloud Free | 0 $/mois, sans carte; 2 000 événements d'authentification et 2 000 appels d'outils par mois. [Tarifs][pricing] | Disponibilité effective de User Sources, contrôles et exports requis dans cette édition. |
| Niveaux supérieurs | Team : 25 $/mois, plus 0,10 $ par événement d'authentification et 0,01 $ par appel. Enterprise : devis; SSO, RBAC et audit explicitement listés. [Tarifs][pricing] | Prix d'un périmètre d'essai donnant toutes les fonctions; aucune dépense autorisée. Le symbole monétaire de la page ne suffit pas à fixer taxes ou devise de facturation du compte. |
| Durée et dépassement | Les conditions affichées, datées du 15 juillet 2025, décrivent Free Trial/Hobby sans limite de temps, mais prévoient un passage automatique au niveau supérieur après dépassement, annoncé avant application. [Conditions][terms] | Correspondance exacte avec le Free actuel et moyen effectif de garantir zéro dépense. Ne pas traiter « sans carte » comme une garantie de plafond bloquant. |
| Environnement | Projet Cloud isolé proposé; administrateur O et employé U distincts. | Organisation, projet, propriétaire, URL et habilitations : non désignés. IdP et site Confluence : non désignés. |

## Configuration à préparer après désignation des comptes

**Identité U.** User Source relie un projet à un IdP OIDC, indépendamment du SSO
administrateur. Prévoir un client OAuth confidentiel, Authorization Code avec
PKCE, `issuer`, `client_id`, secret privé et sujet `sub` stable. Le callback IdP
documenté est `https://cloud.arcade.dev/oauth2/intermediate_callback`; scopes par
défaut `openid profile email`. Une même User Source peut servir plusieurs
passerelles. Valeurs réelles et édition IdP inconnues. [User Sources][users]

**Passerelles et clients.** Prévoir deux configurations MCP isolées utilisant
Streamable HTTP et OAuth navigateur, sous la même identité U. L'URL documentée
est `https://api.arcade.dev/mcp/{slug}`. Arcade Auth exige un membre du projet;
Arcade Headers transmet un identifiant utilisateur fourni par le client et
ne suffit pas au contrôle d'identité retenu. L'allowlist de `client_id` supprime
un écran de consentement : elle ne prouve pas une délégation A/B. Les IDs CIMD
documentés correspondent à des logiciels clients; DCR attribue un ID par
enregistrement. Logiciel, version et enregistrements retenus restent inconnus.
[Passerelles][gateways]

**Connexion Atlassian.** Il n'existe pas d'Auth Provider Atlassian par défaut
dans ce guide : créer une application OAuth propre, saisir client ID/secret
dans Arcade, puis enregistrer **le callback généré par Arcade** dans Atlassian.
Ce callback n'est pas encore connu et ne doit pas être confondu avec celui de
l'IdP. Le guide exige aussi un vérificateur utilisateur adapté en production;
le montage exact User Source/autorisation Atlassian reste à confirmer.
[Fournisseur Atlassian][atlassian]

**Outils proposés.** Commencer par `Confluence.GetPage`, `Confluence.ListPages`
et `Confluence.SearchContent`; ajouter `WhoAmI`/`GetAvailableAtlassianClouds`
seulement si nécessaires au rattachement de U et du site. Le catalogue annonce
Confluence **3.0.2**, 14 outils, lecture, recherche et écritures. N'exposer que
les outils de lecture retenus. Leur sélection seule ne restreint pas les pages
accessibles à U. Version effectivement déployée et schémas effectifs inconnus.
[Catalogue Confluence][confluence]

### Scopes de lecture : candidats, pas configuration validée

La liste minimale exacte du toolkit **n'est pas établie** par les pages publiques
consultées. Avant consentement, exporter ses exigences OAuth pour les seuls
outils retenus, relever les endpoints réellement employés et figer leur union.
Les références Atlassian fournissent ces repères :

| Besoin | Scope documenté côté API | Condition d'emploi |
| --- | --- | --- |
| Liste et lecture de pages v2 | `read:page:confluence` | Minimum de ces endpoints v2, pas preuve que le toolkit les utilise. [Pages v2][pages] |
| Recherche v1 | `search:confluence` classique recommandé; alternative granulaire `read:content-details:confluence` | Choisir selon l'endpoint/exigence réelle, sans cumuler par défaut. [Recherche v1][search] |
| Contenu détaillé avec API classique | `read:confluence-content.all` | Seulement si requis par les appels retenus. [Scopes][scopes] |
| Profil ou espaces | `read:confluence-user`, `read:confluence-space.summary` | Seulement si les outils nécessaires les demandent. [Scopes][scopes] |
| Renouvellement OAuth | `offline_access` | Nécessaire pour obtenir un refresh token; aucune permission d'écriture ajoutée. [OAuth 3LO][oauth] |

Les scopes n'outrepassent pas les permissions Confluence. [Scopes][scopes]
Atlassian documente maintenant des grants au niveau compte **et** des grants
limités aux sites sélectionnés : relever celui obtenu et les sites retournés
par `accessible-resources`; cela ne prouve aucune séparation par agent.
[OAuth 3LO][oauth] Aucun scope d'écriture, gestion ou administration n'est prévu
pour U. Le corpus sera chargé par O, séparément.

## Ce qu'il reste à établir pour S0–S6

| Contrôle | Éléments documentaires | Condition de preuve manquante |
| --- | --- | --- |
| S0 — droits source | Le contrôle direct de U prévu au plan reste nécessaire. | Tenant Confluence, édition permettant D4, O/U et upload autorisés; aucun contrôle source exécuté. |
| S1/S2 — délégations A/B | L'architecture annonce des jetons OAuth limités à une passerelle. C'est un mécanisme candidat pour le contrôle croisé. [Architecture][architecture] | Objet authentifié A/B, possibilité de restreindre D1/D2 par délégation, et refus avec les seuls identifiants de B au point d'entrée A. Deux URL ne suffisent pas. |
| S3 — continuité | Le coffre conserve et renouvelle les jetons fournisseur. [Architecture][architecture] | Lectures effectives après nouvelle conversation, interventions U et maintien de l'identité de chaque délégation. |
| S4 — extension demandée | Les hooks permettent des contrôles avant/après exécution. [Contextual Access][hooks] | Parcours standard de demande durable D2, état consultable et rôle décisionnaire non établis. Ne pas le développer pour terminer l'essai. |
| S5 — retrait de A seul | Une opération de suppression de connexion utilisateur/fournisseur est documentée. [Engine API][engine] | Objet dédié à A et maintien de U/B, sessions ouvertes et nouvelles. Supprimer la connexion partagée n'est pas une réussite. Délai de révocation inconnu. |
| S6 — preuves | Audit administratif et historique d'exécution sont deux surfaces distinctes. [Audit][audit], [Exécutions][executions] | Accès effectif aux exports, liaison U/agent/ressource/décision/résultat, et preuve de nettoyage. |

L'audit administratif fournit notamment événement, horodatage, principal,
type/ID de ressource et action. Il ne remplace pas la trace d'une lecture.
[Audit][audit] Tool Executions documente outil/version, U, résultat, tentatives,
entrées/sorties; ces dernières exigent O administrateur. La rétention Cloud
par défaut est de **sept jours**. Le schéma présenté ne suffit pas à prouver
l'identifiant A/B de chaque appel; vérifier aussi la trace des refus avant
exécution. Exporter les preuves expurgées pendant la campagne sans changer une
politique de rétention partagée. [Exécutions][executions]

## Réutilisation et extension : hypothèses bornées

La réutilisation du runtime et du coffre OAuth mérite un essai si les prérequis
sont levés. Pour restreindre les ressources, Contextual Access propose des
hooks de visibilité, de pré-exécution et de post-exécution appelant **une logique
que l'intégrateur fournit**. Cela reste une extension, hors réalisation de cette
campagne. [Contextual Access][hooks]

Le schéma public HTTP **1.0** consulté contient `user_id`, les données
d'autorisation, les entrées/sorties et `execution_id`; aucun champ dédié
`client_id` ou `gateway` n'y a été trouvé. La provenance d'un signal A/B
authentifié exploitable par cette extension reste donc à établir, même si des
métadonnées extensibles existent. Ce constat borné au schéma consulté ne prouve
pas l'impossibilité du montage. [Schéma officiel][schema]

## Périmètre restant à autoriser

Première décision concrète : désigner un compte/projet Arcade d'essai et son
administrateur, ou autoriser sa création, **avec zéro dépense et arrêt si ce
plafond ne peut pas être assuré**. Ensuite figer les accès nécessaires : IdP
et application OIDC, tenant Confluence adapté, O/U, application Atlassian,
upload D1–D4, consentements, configurations MCP temporaires et appels de lecture.
Aucun de ces comptes ou consentements n'a été inventé ou activé. Un besoin
d'Enterprise payant ou de contact commercial sera soumis séparément.

Inventaire des versions : Confluence toolkit 3.0.2 et schéma hooks HTTP 1.0
documentés; build Arcade Cloud, toolkit réellement servi, IdP, tenant Confluence,
client MCP et SDK : **inconnus/non utilisés**. Les dates de mise à jour des guides
ne constituent pas des versions de service. Bornes du plan conservées : trois
heures de préparation active et deux heures d'essais par offre.

## Sources et limites de recherche

Toutes les sources ci-dessous ont été consultées publiquement le **21 septembre
2026**. Les conclusions reposent sur documentation officielle et schéma officiel;
aucune console ni licence n'a été vérifiée. Recherche ciblée limitée à quinze
minutes; pas de revue exhaustive du code, du catalogue ou des contrats.
Les métadonnées d'outils inaccessibles dans les pages consultées sont laissées
inconnues. Aucun fichier mémoire n'a servi de preuve produit.

[pricing]: https://www.arcade.dev/pricing/
[terms]: https://www.arcade.dev/terms-of-service/
[users]: https://docs.arcade.dev/en/operate/identity/user-sources
[gateways]: https://docs.arcade.dev/en/operate/governance/mcp-gateways
[atlassian]: https://docs.arcade.dev/en/references/auth-providers/atlassian
[confluence]: https://docs.arcade.dev/en/resources/integrations/productivity/confluence
[pages]: https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-page/
[search]: https://developer.atlassian.com/cloud/confluence/rest/v1/api-group-search/
[scopes]: https://developer.atlassian.com/cloud/confluence/scopes-for-oauth-2-3LO-and-forge-apps/
[oauth]: https://developer.atlassian.com/cloud/confluence/oauth-2-3lo-apps/
[architecture]: https://docs.arcade.dev/en/operate/deploy/architecture
[hooks]: https://docs.arcade.dev/en/operate/governance/contextual-access
[engine]: https://docs.arcade.dev/en/resources/integrations/development/arcade-engine-api
[audit]: https://docs.arcade.dev/en/operate/governance/audit-logs
[executions]: https://docs.arcade.dev/en/operate/governance/tool-executions
[schema]: https://github.com/ArcadeAI/schemas/blob/main/logic_extensions/http/1.0/schema.yaml
