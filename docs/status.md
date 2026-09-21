# État du projet

Mise à jour : 21 septembre 2026, après implémentation du parcours d'accès dans
le workspace. La suite du pilote a été exécutée à nouveau pour ce lot; les
résultats des campagnes antérieures restent leurs preuves datées.

## Disponible et validé localement

| Composant | Résultat | Preuve |
| --- | --- | --- |
| Pilote email MCP | Broker OPA/SQLite, MIME figé, quatre outils MCP, canal humain Unix et fournisseur simulé | [Validation initiale](../pilot-results/codex-email/20260920-steps-1-2/REPORT.md) |
| Préparation Linux | Permissions du socket, surveillance d'OPA, reprise, unité et sondes livrées; contrôles locaux sous un UID | [Intégration A/B/C](../pilot-results/parallel-workstreams/integration-20260920/REPORT.md) |
| Laboratoire web | Parcours manipulé par l'assistant, observation de la boîte reçue, neuf scénarios E2E; 102 tests du pilote réussis | [Validation du laboratoire](../pilot-results/local-lab/20260920/REPORT.md) |
| Demande d'accès agent | Six outils MCP, demande persistante, décision simulée, récupération HTTP fictive et lecture seule; 122 tests réussis. Demande Codex native puis même accès lu dans deux conversations, une seule récupération fournisseur | [Validation du lot](../pilot-results/codex-email/20260921-agent-access/REPORT.md) |
| Qualification d'inspection | Corpus de 24 cas fictifs français/anglais, validation de prédictions fournies, métriques; 13 tests et 13 824 combinaisons vérifiés | [Livraison C](../pilot-results/parallel-workstreams/C/REPORT.md) |

La suite du pilote est passée de 64 tests initialement à 96 après préparation
Linux, puis 102 avec le laboratoire et 122 avec les demandes d'accès. Les neuf scénarios sont exécutés aussi par
un des tests du lab; ces nombres ne sont pas des totaux à additionner.

Le parcours assisté utilise l'IA de la session pour rédiger après une vraie lecture
MCP; la campagne automatique utilise des réponses scriptées. Aucun serveur de
modèle, clé API de modèle ou compte email distant n'est nécessaire au laboratoire.
L'installation initiale des dépendances peut accéder à leurs distributions publiques.

## Proposé ou restant à qualifier

- **Ingestion/inspection** : le [contrat B](plans/email-ingestion-contract.md) a
  été techniquement revu, mais reste sans acceptation produit et sans code
  d'ingestion MIME. Le parcours d'envoi reçoit encore ses ressources par
  `create_grant`; le parcours d'accès récupère des objets JSON fictifs après
  accord humain. Cela ne qualifie pas le contrat d'ingestion réelle.
- **Détection** : la couche d'inspection et le rôle de Prompt Guard sont retenus. Variante,
  poids, runtime, seuils et performances restent à qualifier. Le banc de
  prédictions n'exécute aucun modèle; ses exemples artificiels ne prouvent pas
  une détection ni une immunité aux injections.
- **Isolation système** : installation sous des UID distincts, supervision
  systemd, accès des outils de l'agent et sondes réelles restent à valider. Le
  lab et ses tests sous un UID ne démontrent pas ces propriétés.
- **Client et fournisseur externes** : demande et lectures ont été observées
  dans Codex avec MCP configuré uniquement pour le processus et canal humain
  simulé. Consentement humain indépendant, OAuth/Gmail, configuration persistante
  et livraison email réelle restent hors du lot.
- **WebMCP** : les deux outils de navigateur facultatifs du lab n'ont pas été
  qualifiés faute de support du navigateur utilisé; les boutons ont été testés.

## Deux séries A/B/C distinctes

| Lettre | Prototypes historiques dans `experiments/` | Lots d'intégration récents |
| --- | --- | --- |
| A | Module embarqué apparitor/Cedar | Préparation de l'isolation Linux, code livré |
| B | Broker OPA indépendant, origine du pilote | Contrat d'ingestion, proposition seulement |
| C | Capabilities Biscuit | Banc de qualification hors modèle, code livré |

Les trois lots récents ont été intégrés et publiés sur la base
`f4350fe37d285598ebe5ef9e3253ac2af12e3b35`. Leur publication n'a pas accepté le
contrat produit B. Le laboratoire et cette réorganisation documentaire sont
postérieurs à cette base; consulter Git pour leur état de publication effectif.

## Continuer

Le [guide du lab](pilot/local-lab.md) permet de rejouer un parcours, provoquer une
panne, observer les événements/MIME et vérifier une correction. C'est le point
de départ pour poursuivre les tests locaux avec l'assistant.

Les autres suites possibles correspondent à des travaux distincts : décider le
contrat d'ingestion avant son développement, qualifier un détecteur à partir du
banc, ou exécuter le runbook sur une installation Linux séparée. Un guide ou un
plan historique ne constitue pas une autorisation d'exécuter ces étapes.
