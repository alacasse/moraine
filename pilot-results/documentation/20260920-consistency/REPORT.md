# Contrôle de cohérence documentaire après migration

20 septembre 2026. Contrôle demandé après le déplacement des guides dans
`docs/`. La première revue avait vérifié l'organisation, les liens et les
distinctions principales; elle n'avait pas éliminé tous les écarts de contenu.
Ce passage a trouvé et corrigé les points ci-dessous, sans modifier le code.

## Périmètre et méthode

Les 42 documents actifs (`README.md`, `AGENTS.md` et Markdown sous `docs/`)
forment le périmètre du contrôle croisé. L'[état courant](../../../docs/status.md)
sert de point d'entrée pour distinguer livré, proposé et restant à qualifier;
les sources et preuves datées tranchent les affirmations techniques.

- Revue indépendante des six plans, deux prompts et points d'entrée :
  statut des décisions, mandats, lettres A/B/C, livraisons et limites.
- Revue indépendante des guides pilote, architecture et qualification face
  au code : contrats, états, bornes, rôles, commandes, preuves et compteurs.
- Contrôle du coordinateur sur les recherches et expériences : portée des
  affirmations, chronologie, recommandations, résultats avant/après revue et
  correspondance avec le pilote courant.
- Contre-revue des corrections par les deux reviewers : constats clos,
  aucune incohérence nouvelle identifiée dans leur périmètre.

## Écarts corrigés

| Document | Écart | Correction |
| --- | --- | --- |
| Plan pilote, §§7–8 | Étapes déjà livrées encore décrites comme futures, avec une autorisation de développement à obtenir | Découpage initial explicite, étapes 1–2 réalisées, chemins documentaires actuels, qualification Linux encore distincte |
| Plan pilote, §6 | Contrat d'ingestion annoncé non défini alors qu'une proposition revue existe | Proposition B disponible, toujours non acceptée et non implémentée |
| Recherche inspection | Refus des emails HTML-only attribué au pilote actuel | Limite du contrat d'ingestion proposé; le pilote reçoit du texte par le canal humain, sans parsing entrant |
| Recherche inspection | Constitution du corpus présentée comme entièrement future | Corpus et évaluateur C livrés; essai de détecteur encore à réaliser |
| Interface et architecture | `processing` présenté sans distinguer sa projection; aperçu promis pour tout `pending` | État interne projeté en `unknown/unresolved_dispatch_intent`; champs sensibles conditionnels |
| Interface | Borne générale de 128 caractères pour les identifiants, sans exception | `message_id` jusqu'à 254 octets ASCII; version entière entre 1 et `2**53-1` |
| Guide du lab | Même arrêt décrit pour CLI et console | Console : fin du scénario courant; CLI : interruption, nettoyage et code 130 |
| Guide du lab | Emplacement du résumé et présence des rapports trop absolus | Emplacements CLI/console séparés; diagnostics et références de preuve conditionnels après échec d'initialisation |
| Recherche initiale et contrats/plans expérimentaux | Présent historique ambigu : aucun code/Git, mandats de développement | Portée historique explicite et liens vers les livraisons ultérieures |
| Comparaison expérimentale | Préférence pour A sans lien direct vers le choix ultérieur de B | A reste le candidat embarqué de cette comparaison; B est la base du service MCP livré |
| Plan pilote | Fournisseur synthétique dédupliquant sans préciser lequel | Fournisseur historique A/B/C distinct du fournisseur du pilote sans déduplication |
| Guide du broker expérimental B | `run.sh --inexact` présenté comme une option de lancement | Option de `uv sync` utilisée en interne par le script |

Les différences historiques ne sont pas effacées : compteurs avant/après
correction, Python 3.13 pour l'expérience Biscuit et 3.14 pour le pilote,
fournisseurs de test distincts, et deux séries A/B/C conservent leur contexte.
La publication des lots n'accepte pas le contrat produit B. Le rôle de Prompt
Guard reste retenu, sans variante ni intégration qualifiée. Les résultats du
lab ne prouvent ni isolation multi-UID, ni ingestion, ni livraison email réelle.

## Vérifications et conservation

Le [manifeste de ce contrôle](manifest.json) enregistre les empreintes finales,
les fichiers modifiés et les résultats des vérifications de liens/ancres et de
syntaxe des blocs shell. Les blocs shell sont analysés avec `bash -n`, pas exécutés.
Aucune suite applicative ni campagne E2E n'a été relancée pour ces corrections.
Les résultats métier cités demeurent ceux de leurs campagnes datées.

La [capture préalable](documentation-before-audit.zip) conserve les 42 fichiers
dans l'état exact décrit par le [registre de migration](../20260920/migration.json).
Ce registre et son archive restent inchangés. Les 503 fichiers applicatifs et
preuves protégés lors de la migration, ainsi que les 34 artefacts du laboratoire,
sont contrôlés par empreinte. Les 14 sources du manifeste historique du lab
restent vérifiables depuis l'archive avant migration.

Aucune contradiction résiduelle n'a été identifiée dans les points examinés.
Ce constat est une revue de cohérence interne, pas une preuve d'exhaustivité
ni une nouvelle qualification des dépendances externes. Les recherches
conservent leurs dates; leurs sources externes n'ont pas été consultées à nouveau.
