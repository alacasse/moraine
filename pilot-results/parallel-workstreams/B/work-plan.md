# Lot B — plan de travail documentaire

Date : 2026-09-20. Statut : revue préalable confirmée par `review_authority`; rédaction autorisée dans le mandat documentaire.
Base : b63590cc02dbcb31859aeb683f4f71314beeb775; worktree :
`/home/alacasse/.codex/worktrees/49ae/moraine`; état initial propre.
Racine documentaire : `docs` (configuration locale absente, pas de docs/AGENTS.md).
Code et documentation : même dépôt Moraine. Aucun graphe existant; pas de construction.

## Livrable et frontières

Rédiger exclusivement `docs/plans/email-ingestion-contract.md` et les preuves
sous `pilot-results/parallel-workstreams/B/`. Ne changer aucun fichier existant
partagé, de production, d'instructions ou historique; aucun commit/publication.
Contrat **proposé**, la revue technique ne vaut pas décision produit.

## Méthode

1. Comparer le cadrage du pilote §6/§10 et la note de recherche aux chemins
   `create_grant`, `list_context`, `read_context`, validation et stockage actuels.
2. Définir sources, données inspectées, validation MIME, bornes proposées,
   fidélité, provenance, résultat typé et politique séparée de l'autorisation.
3. Décrire publication atomique, révocation/expiration pendant analyse,
   invalidation/cache, erreurs, rétention et reprise. Expliciter les nouvelles
   surfaces humaines et persistantes, sans les présenter comme acceptées.
4. Décomposer une future implémentation avec un faux inspecteur et des oracles
   indépendants de ses scores. Ne pas qualifier ni exécuter de modèle.
5. Faire relire le résultat par deux reviewers distincts de l'auteur :
   autorité/publication et implémentabilité/tests. Inclure tous les fichiers
   non suivis, corriger les constats et obtenir confirmation de résolution.
6. Vérifier liens locaux, périmètre et whitespace; enregistrer commandes,
   résultats et limites. Terminer par une décision produit prioritaire.

## Critères mesurables du document

- Aucun chemin de publication omettant corps, métadonnées ou note.
- Table explicite des alertes, pannes, sorties invalides et couverture partielle.
- Lien source/extraction/publication/inspection/version; aucun score n'accorde
  un droit; refus après révocation ou expiration, même si analyse réussie.
- Plan de démonstration couvrant cache, changement de règles, erreur/crash,
  alerte, révocation concurrente et faux avis favorable sans élargir les droits.
- Surfaces nouvelles chiffrées conceptuellement, hypothèses marquées et une
  recommandation produit prioritaire; aucune dépendance imposée aux lots A/C.

## Évidence à conserver

Revue préalable et deux revues finales attribuées aux agents; journal des
résolutions; résultats de contrôles documentaires réels. Les tests futurs
restent des critères, jamais des tests annoncés exécutés.

## Revue préalable

Reviewer distinct : `/root/review_authority`, lecture seule, avant rédaction
du contrat. Conclusion : « Prêt pour rédaction documentaire. Aucun constat
bloquant. » Il demandait de concrétiser sélection pré-grant, finalisation
atomique, relecture courante après analyse et séparation publication/envoi.
Ces points sont traités dans les sections 1, 5 et 6 du contrat proposé.
