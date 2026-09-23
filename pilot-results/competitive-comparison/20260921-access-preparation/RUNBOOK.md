# Reprendre la collecte S0–S6

Ce support prépare les gestes; **aucune étape externe n'a été exécutée**.
Le [mandat](MANDATE.md) activé par l'utilisateur autorise la préparation locale.
Le [plan figé](PLAN.md) conserve son ancien statut de plan non exécuté : le
mandat courant et les autorisations consignées déterminent l'exécution.
Les liens internes des captures se résolvent depuis leur chemin d'origine
dans le manifeste, pas depuis ce dossier.

## Matériel préparé

- [Corpus](corpus/index.json) : quatre textes fictifs, identifiants logiques,
  marqueurs distincts de titre/corps et droits attendus. Les IDs Confluence et
  versions restent `null` jusqu'à la publication autorisée.
- [Configuration](configuration.redacted.json) : projet/workspace, identité U,
  deux délégations A/B, scopes et connexions à relever; aucune configuration
  appliquée. Ne jamais mettre de secret dans ce fichier.
- [Cas](collection/cases.json) : 126 contrôles prévus, comprenant les lectures
  sous U, S2/S3, puis B visant A. Ce nombre n'est pas un nombre de tests passés.
- [Modèle de relevé](collection/observation-template.json) : un enregistrement
  par appel, avec couche de décision, données reçues, preuve serveur et coût
  d'intervention. Les champs inconnus restent `null`; zéro signifie mesuré nul.
- [Observations source](collection/source-observations.json),
  [transcriptions](collection/transcripts.redacted.json) et
  [registre des ressources](collection/resource-register.json) : vides car
  non essayés. Ne pas compléter par des prédictions.

## Conditions avant une exécution externe

Consigner l'autorisation et les comptes nommés, l'édition réellement active,
l'échéance d'essai et le budget accepté. Les fiches
[source](source-prerequisites.md), [Arcade](arcade-prerequisites.md) et
[Workato](workato-prerequisites.md) détaillent les inconnues. La source peut
être préparée indépendamment; chaque candidat exige ensuite son propre
périmètre autorisé, y compris les scopes effectivement demandés.

Utiliser un runtime neuf, privé et hors dépôt. Exemple local, seulement lors
de la reprise nécessitant des secrets :

```bash
umask 077
mktemp -d /tmp/moraine-comparison.XXXXXXXX
```

Ne placer dans Git ni jetons, cookies, en-têtes Authorization, paramètres de
callback contenant un code, ni exports de comptes. Garder les réponses brutes
privées et produire une transcription expurgée, en conservant résultat,
identifiants synthétiques, marqueurs et association aux traces. Ne pas retirer
les données hors périmètre d'une réponse avant de conclure sur une fuite.
Les marqueurs attendus appartiennent au contrôleur de test; ne jamais fournir
les corps du corpus, les réponses attendues ou ces fichiers à l'agent évalué.

## Gestes reproductibles

1. **S0.** O crée les trois espaces et les quatre pages depuis `corpus/`,
   relève IDs/versions et droits; U, dans une session distincte, tente recherche,
   liste et lecture par ID pour chaque page. Consigner corps **et** métadonnées.
   Vérifier U non administrateur et droits encore inchangés après les essais.
   Un témoin sans contrôle initial reste bloqué séparément.
2. **S1.** Relever les versions réelles du client, du SDK/transport et des
   outils exposés. Configurer deux clients isolés avec le même U. Inspecter
   `tools/list`, conserver noms, schémas et scopes sans appeler d'écriture.
   Identifier la preuve authentifiée distinguant A/B, la connexion fournisseur
   et l'objet révocable. Une URL distincte ou un champ d'agent ne suffit pas.
   Si la séparation ne peut être établie, consigner la limite sans contourner
   le problème avec deux U ou une restriction supplémentaire dans Confluence.
3. **S2.** Pour chaque cas applicable, appeler l'outil effectif de lecture,
   recherche ou liste avec un client MCP diagnostic sans filtrage local.
   Résoudre les arguments depuis le schéma exposé, sans inventer noms d'outils
   ou IDs. Donner directement l'ID même si la recherche ne révèle pas la page.
   Parcourir la pagination nécessaire au corpus. Pour recherche, conserver
   requête et résultats; pour liste, vérifier également les métadonnées.
   B vise ensuite le sélecteur public de A avec **uniquement les identifiants
   de B**, sans consentement nouveau. Conserver la preuve serveur de délégation
   B. Si la substitution est inapplicable, justifier et trouver une preuve
   serveur équivalente; sinon verdict « non établi ».
4. **S3.** Fermer les conversations, ouvrir des contextes vides sans donner
   le corpus et reprendre les mêmes appels sous chaque identité configurée.
   Distinguer réauthentification U, nouvelle intervention O, cache et lecture
   actuelle. Si un client natif est disponible et autorisé, demander à A une
   synthèse D1/D2 et à B une synthèse D1, avec leurs appels réels conservés.
   Aucun résultat de modèle ne remplace une réponse d'outil.
5. **S4.** B demande D2 par le mécanisme natif disponible; ne prendre aucune
   décision. Relever demande persistante, état consultable et rôle habilité.
   Refaire la lecture D2 : aucun droit ne doit avoir changé. Si le parcours
   natif n'est pas établi, le noter; ne développer ni hook ni recette.
6. **S5.** Vérifier avant retrait que sessions et grants resteront valides
   pendant plus de cinq minutes. Confirmer compte/droits source U et B.
   Retirer uniquement la délégation A, ou sa connexion propre, sans révoquer
   une connexion commune. Horodater la confirmation. Faire de nouvelles
   lectures A de D1/D2 dans contexte ouvert et vide à 0, 5, 30, 60, 300 s,
   arrêter les intermédiaires après le premier refus, garder le contrôle de
   stabilité à 300 s. Contrôler B (D1 accepté/D2 refusé) à 0 et 300 s et U à
   la source. Aucun renouvellement d'autorisation caché. Une erreur réseau,
   une expiration ou un refus volontaire du modèle ne prouve pas le retrait.
7. **Reprise ciblée.** Si le budget le permet, rétablir explicitement les
   droits initiaux, consigner cette intervention et rejouer S2/S3/S5 une
   seconde fois. Sinon : « une seule observation ». À toute divulgation
   inattendue, interrompre le cas, conserver les faits et revoir la
   configuration; reproduction limitée au tenant fictif autorisé.
8. **S6.** Associer appel, U, A/B, ressource, décision et résultat aux traces
   disponibles; préciser les champs manquants. Exporter les preuves expurgées,
   puis supprimer uniquement les objets dont le registre prouve la création
   dans cet essai. Vérifier le retrait de connexions et configurations. Ne
   supprimer ni compte existant ni ressource d'une autre campagne.

## Mesures et limites

Chronométrer séparément lecture, configuration, scénarios et attente externe,
par candidat. Plafonds : trois heures actives de préparation puis deux heures
de scénarios; attendre un accès ne vaut pas du temps de configuration.
Compter actions O, authentifications U, consentements U, modifications manuelles
U, connexions, appels et coûts réellement constatés. Une surface absente se
note absente, pas « refus observé ». Une édition inaccessible se note bloquée.
Une extension possible est une hypothèse de travail à estimer séparément.

Ne pas écraser cette campagne partielle après livraison. Pour les observations
externes ultérieures, créer un nouveau dossier de campagne et référencer celui-ci.
