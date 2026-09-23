# Revue du plan de comparaison Arcade / Workato

Date : **21 septembre 2026**. Mandat : planifier puis faire reviewer par un
autre agent; aucun mandat d'exécuter les essais ni de publier ce lot.

**Verdict final du reviewer : plan prêt à proposer.** Première revue : deux
P2 et un P3. Corrections effectuées, puis seconde revue : aucun constat
résiduel P1/P2/P3. Cela qualifie le plan, pas les produits ni leur marché.

## Documents et indépendance

- [Plan maintenu](../../../docs/plans/agent-access-competitive-comparison.md).
- [Étude de marché](../../../docs/research/enterprise-agent-access-market.md),
  préparée précédemment par `/root/enterprise_market_research`.
- [Prérequis vérifiés](../../../docs/research/agent-access-comparison-prerequisites.md),
  recherche complémentaire du même agent; protocole harmonisé par le rédacteur.
- Reviewer : `/root/review_competitive_comparison_plan`, agent distinct du
  rédacteur et du chercheur, lancé sans historique de rédaction. Revue en
  lecture seule, puis contre-revue par ce même reviewer sur une nouvelle capture.

Le checkout de référence est `29a883450f585fc6662e151de133559670fc5864`.
La recherche de marché était déjà présente non commitée; ses bytes sont
préservés. Aucun code, configuration d'agent ou document d'instructions modifié.

## Versions et corrections

| Capture | Empreinte SHA-256 | Verdict conservé |
| --- | --- | --- |
| [PLAN-v1.md](PLAN-v1.md) | `cd4b31c6a0dd17483e260134504c7f50be11b7b378de12ca00faf1aaa604a6f7` | [Révision ciblée nécessaire](REVIEW-v1.md) |
| [PLAN-v2.md](PLAN-v2.md) | `24b480003e61d742b8bb24af7f9ecfa2580e84069f9f6e045a7ac79549eea497` | [Prêt à proposer](REVIEW-v2.md) |

| Constat initial | Correction dans v2 |
| --- | --- |
| P2 : deux configurations ordinaires pourraient masquer des identifiants donnant les mêmes droits | Contrôle B vers le point d'entrée/sélecteur de A, avec les seuls identifiants de B; preuve serveur ou séparation non établie. |
| P2 : une connexion fournisseur commune était imposée | Connexions distinctes admises; mesurer les consentements et retirer A en conservant U et B. |
| P3 : un tenant Confluence Free ne permet pas le témoin réservé à l'administrateur | Édition source et fin d'essai à vérifier; U ordinaire distinct de O; D4 bloqué séparément si nécessaire. |

Les deux comptes rendus conservent les conclusions du reviewer, leurs limites
et les vérifications qu'il déclare avoir faites. Les captures ne sont pas
réécrites après correction. Les copies [MARKET.md](MARKET.md) et
[PREREQUISITES.md](PREREQUISITES.md) figent les recherches lues. Les liens relatifs
internes à ces captures documentaires conservent leurs bytes d'origine : les
résoudre depuis les emplacements indiqués dans le [manifeste](manifest.json),
ou utiliser les documents maintenus ci-dessus pour la navigation.

## Validation et frontière de livraison

L'agent principal a vérifié les liens locaux des documents maintenus et des
comptes rendus, l'identité byte à byte du plan avec v2, les empreintes des
captures et la conservation de la recherche de marché préexistante.
`git diff --check` ne relève pas d'erreur. Les références externes fondant les
prérequis ont été consultées dans la recherche; la limite Confluence a également
été vérifiée pendant la revue et la correction.

Aucune suite métier n'a été relancée pour ce lot documentaire. Aucun produit
comparé n'a été essayé; aucun compte créé, achat, installation, connexion OAuth
ou contact fournisseur réalisé. Les disponibilités, coûts et permissions
effectives restent des prérequis explicites pour une éventuelle exécution.
Le plan et les preuves restent locaux; aucun commit/push demandé pour ce lot.
