# Lot B — provenance et revue du contrat d’ingestion

Date : 2026-09-20. **Plan proposé et revu; aucune acceptation produit.**
Les deux contre-revues ont confirmé la résolution des constats. Les contrôles
finaux et leur portée sont consignés ci-dessous.

## Base, propriété et résultat

- HEAD vérifié : `b63590cc02dbcb31859aeb683f4f71314beeb775`, identique au mandat.
- Worktree : `/home/alacasse/.codex/worktrees/49ae/moraine`, initialement propre.
- Documentation et code : même dépôt Moraine. `codex.docs-root` absent : `docs`;
  aucun `docs/AGENTS.md` ni fichier d’instructions imbriqué trouvé dans les
  répertoires concernés. Instructions personnelles lues et respectées.
- `codex-owner` consulté avant écriture pour le contrat et le répertoire B :
  `external-or-unmanaged`, aucun lien de configuration à éditer.
- Livrable : [contrat proposé](../../../docs/plans/email-ingestion-contract.md).
  [Plan de travail](work-plan.md) relu avant rédaction.
- Seulement nouveaux fichiers du lot B; aucune production, instruction,
  expérience historique, dépendance ou lock modifié. Aucun commit/push/fusion.

## Sources et portée de l’analyse

Lecture du découpage partagé dans le checkout source
`/home/alacasse/projects/moraine/docs/plans/parallel-workstreams.md` (non modifié),
du pilote §6/§10 et parcours utile, de la note de recherche d’inspection, du
broker `create_grant/list_context/read_context/projection/propose_reply/review`,
des modèles de validation, de la politique Rego, de l’adaptateur simulé, du
transport humain et des tests de cycle existants. Ces tests ont été lus, pas
exécutés. Aucun résultat historique n’est présenté comme une nouvelle preuve.

Consultation des consignes Graphify; aucun graphe existant, aucune construction,
conformément au mandat. Recherche mémoire ciblée `moraine|email-ingestion` sans
résultat pertinent, aucune mémoire utilisée comme source du contrat.
Aucune nouvelle affirmation sur une bibliothèque externe nécessaire : pas de
navigation externe, téléchargement ou qualification de version. Le document
s’appuie sur le cadrage existant et propose un contrat propre à Moraine.

## Provenance des revues indépendantes

Auteur : agent principal `/root` de cette tâche. Reviewers distincts de l’auteur,
en lecture seule, partageant le worktree; consigne explicite de ne modifier
aucun fichier. Les revues portent sur les fichiers non suivis, pas seulement
sur un diff Git qui serait vide.

| Phase | Reviewer | Résultat et portée |
|---|---|---|
| Avant rédaction | `/root/review_authority` | « Prêt pour rédaction documentaire. Aucun constat bloquant. » Vérification du mandat, plan de travail, cadrage, sources et broker. Points à concrétiser : sélection pré-grant, publication atomique, relecture courante, séparation des revues |
| Contrat — autorité/publication | `/root/review_authority` | Un P2 : une nouvelle sélection identique pouvait contourner l’alerte précédente. Aucun P1 ni autre P2 |
| Contrat — implémentabilité/tests | `/root/review_implementation` | Deux P2 : ambiguïté des retries/budgets; même risque de contournement d’alerte. Aucun P1 |
| Contre-revue autorité | `/root/review_authority` | P2 confirmé résolu après relecture §5/§7/§8/§10; aucun P1/P2 restant, aucune acceptation produit |
| Contre-revue implémentabilité | `/root/review_implementation` | Les deux P2 confirmés résolus après relecture; aucun P1/P2 restant, aucune acceptation produit |

Constats et résolutions intégrées :

1. **Alerte persistante entre sélections.** Un marqueur bloquant par
   compte/source/digests/profil survit au cache absent, au redémarrage et à la
   purge du rapport. Pas d’effacement par un score ultérieur favorable. Nouvelle
   entrée ou révision explicitement qualifiée nécessaire; oracle deux sélections
   alerte puis favorable. Contrat §5, §7, §8, §10.
2. **Réessais et bornes.** Une seule tentative par sélection, 30 s de budget
   total et 384 Kio de rapports; aucun `held → analyzing`, aucun retry réseau
   automatique. Nouvelle sélection explicite pour nouvel essai; le quota global
   compte les rapports précédents. Oracle de timeout/consultation répétée.
   Contrat §4, §5, §6, §10.

Les messages et conclusions des reviewers sont conservés dans l’historique de
cette tâche; ce rapport en donne les constats et confirmations, sans prétendre
qu’une revue documentaire constitue une validation d’implémentation.

## Commandes et vérifications réellement effectuées

- `pwd`, `git status --short`, `git rev-parse HEAD`,
  `git config --local --get codex.docs-root` : base conforme, worktree propre,
  configuration absente; absence traitée comme retour au défaut `docs`.
- `rg --files` et lectures ciblées `cat`/`sed` : instructions, sources et chemin
  broker ci-dessus. Absence de graphe/instructions imbriquées vérifiée.
- `/home/alacasse/.codex/bin/codex-owner <cible>` : deux cibles B hors gestion
  codex-config; aucune configuration installée modifiée.
- Contrôle Python des liens Markdown locaux du contrat : **4 liens résolus**.
- `git diff --check` : aucune erreur sur fichiers suivis; cela ne couvre pas
  seul les nouveaux fichiers. Contrôle complémentaire final des fichiers non
  suivis, liens et périmètre enregistré dans [validation.txt](validation.txt).

Aucun test applicatif, service, modèle, poids, API, email réel ou compte lancé.
Aucune installation, configuration système/Codex ou connexion de compte.
Les tests du §10 sont un futur parcours d’acceptation, **non exécuté**.

## Décision proposée et dépendances pour intégration

Priorité : **publication sans dérogation dans v1**, bloquée sur alerte, panne ou
couverture incomplète. Cette recommandation reste à comparer à l’hypothèse du
coordinateur d’une revue humaine sur alerte. Son coût en faux positifs et
indisponibilité est explicite au §11. Le §5 chiffre l’alternative : 2 verbes et
1 type de décision durable, nonce/digest/échéance distincts de l’envoi.

Impacts nouveaux proposés : §6, 3 opérations humaines de sélection et adaptation
de `create_grant`; §8, 3 familles persistantes, rétention/quotas et reçus d’alerte;
§9, sous-lots B1–B5 et fichiers réservés au coordinateur. Ni A ni C n’a à coder
ce cycle maintenant. Le schéma d’évaluation C n’est pas imposé comme API de B.

Intégration ultérieure : décision produit, autorisation d’implémentation,
consolidation broker/stockage/transports avec A, tests simulés, puis qualification
d’un profil réel et accord sur confidentialité/rétention. Les artefacts de B
peuvent être repris tels quels sans modifier les preuves historiques; l’ajout
d’un lien dans un document partagé appartient au coordinateur.
