# Revue indépendante — première version

Date : 21 septembre 2026. Agent distinct :
`/root/review_competitive_comparison_plan`, lancé sans historique de rédaction.
Compte rendu du reviewer conservé par l'agent principal. Les références de
lignes désignent [PLAN-v1.md](PLAN-v1.md), pas le plan corrigé.

## Verdict du reviewer

**Révision ciblée nécessaire avant de proposer l'exécution.** Le plan est
concret, proportionné à un pilote de découverte et prudent dans ses conclusions.
Deux précisions conditionnent toutefois la valeur de la comparaison : la
preuve opérationnelle de séparation A/B et la neutralité du critère de
révocation envers l'organisation des connexions. Les comptes ou éditions
encore indisponibles sont correctement traités comme des prérequis; leur
absence ne constitue pas un défaut du plan. Aucun constat P1.

Checkout : `29a883450f585fc6662e151de133559670fc5864`.
SHA-256 calculé et revérifié par le reviewer :
`cd4b31c6a0dd17483e260134504c7f50be11b7b378de12ca00faf1aaa604a6f7`.

## P2 — Contrôle explicite du rattachement des droits à A/B

Lignes 70–76 et 157–158, S1/S2. Le texte exige correctement une preuve
authentifiée côté serveur, mais les gestes prescrits vérifient principalement
chaque agent dans sa configuration habituelle. Une configuration pourrait
présenter deux points d'entrée correctement filtrés tout en acceptant les
mêmes identifiants utilisateur sur les deux. Les lectures normales
respecteraient alors la matrice sans démontrer que B est effectivement limité.

La documentation Arcade distingue sélection d'outils par passerelle et
authentification utilisateur; celle de Workato décrit des groupes utilisateur
aux niveaux serveur et outil. Ces descriptions ne prouvent pas une séparation
par agent d'un même utilisateur.
[Arcade](https://docs.arcade.dev/en/operate/governance/mcp-gateways),
[Workato](https://docs.workato.com/en/mcp/mcp-gateway).

Correction minimale : ajouter à S2 un contrôle avec les seuls identifiants
propres à B, en visant le point d'entrée ou le sélecteur public associé à A,
lorsque cette substitution existe. Rester dans le tenant autorisé, sans copier
les secrets de A ni obtenir une nouvelle autorisation humaine. B doit rester
incapable de lire D2. Conserver l'élément serveur rattachant la décision à la
délégation. Si ce contrôle ou une preuve équivalente n'est pas accessible,
qualifier la séparation « non établie ». Cela rend testable l'exigence déjà
posée, sans élargir l'essai à un audit de sécurité.

## P2 — Ne pas imposer une connexion fournisseur commune

Ligne 161, S5. La formulation « sans retirer […] la connexion fournisseur
commune » suppose une organisation particulière. Le besoin porte sur deux
délégations de la même personne, pas sur le partage obligatoire d'un objet de
connexion. Deux connexions OAuth distinctes, toutes deux rattachées à U,
pourraient satisfaire la matrice puis permettre de retirer uniquement celle
de A. Le traiter automatiquement comme une alternative non équivalente
créerait un faux écart concurrentiel. C'est un risque du critère, pas une
affirmation que les candidats proposent effectivement ce montage.

Correction minimale : préserver le compte et les droits source de U ainsi que
tous les accès de B. Préserver une connexion commune lorsqu'elle existe;
autoriser le retrait d'une connexion propre à A lorsqu'elle matérialise sa
délégation. Consigner nombre de connexions, consentements supplémentaires,
objet révoqué et couche responsable. Cette formulation conserve le résultat
utilisateur attendu et mesure le coût des architectures différentes.

## P3 — Édition Confluence nécessaire à D4

Lignes 78–98, 110–115 et 156. Confluence Free ne permet pas de personnaliser
les permissions et restrictions; un tenant gratuit neuf ne suffit donc pas
à construire librement le témoin D4 réservé à O.
[Permissions Confluence](https://support.atlassian.com/confluence-cloud/docs/what-are-confluence-cloud-permissions-and-restrictions/).

S0 empêchera déjà d'attribuer ce problème aux passerelles : il ne bloque pas la
logique du protocole, mais peut consommer le temps de préparation. Ajouter à
la fiche préalable l'édition source permettant la matrice, la durée d'essai
et ses conditions de facturation. Vérifier que U est ordinaire, distinct de O.
Sinon marquer D4 bloqué par le prérequis source, sans affaiblir le contrôle.

## Points solides et limites du reviewer

La comparaison avec Moraine est loyale : les lignes 52–61 bornent sa preuve
à une identité, deux conversations, des captures et un fournisseur fictif.
Le contrat et le rapport conservé corroborent ces limites. Pas de démonstration
multi-agent ni de classement ergonomique fabriqué à partir du pilote.

La matrice distingue restrictions propres à l'agent et droits source. Appels
directs, métadonnées et lectures par ID évitent de prendre un refus du modèle
pour une autorisation serveur. S5 prévoit fenêtre d'observation, maintien de B
et distinction entre révocation, expiration et panne. Les données déjà reçues
ne sont pas présentées comme rappelables.

Les prérequis Workato sont prudents : VUA requiert Workato Identity, exclut les
jetons API et présente la limite indiquée pour les recettes imbriquées.
[VUA](https://docs.workato.com/en/mcp/verified-user-access).
L'exclusion du développement d'extensions borne l'effort, en conservant la
catégorie « documenté avec extension » : les contrôles contextuels Arcade
reposent sur des extensions.
[Contextual Access](https://docs.arcade.dev/en/operate/governance/contextual-access).

Les conclusions commerciales restent des hypothèses, sans transformer un
résultat technique en demande solvable ou choix entre particuliers et entreprises.

Vérifications déclarées par le reviewer : consignes, index, règles documentaires,
deux recherches, état, architecture, contrat et rapport Moraine; comparaison
byte à byte des trois captures avec leurs documents d'origine; cinq guides
officiels cités; `git diff --check` sans erreur. Aucun fichier modifié, test
métier, compte, installation, service ou contact externe. Cette revue ne valide
aucune offre et n'autorise aucun essai.
