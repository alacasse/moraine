# Laboratoire local de bout en bout

Statut : implémenté et validé localement le 20 septembre 2026; modifications
non commitées sur `codex/local-e2e-lab`. Voir le
[rapport de validation](../../pilot-results/local-lab/20260920/REPORT.md).
Base : `f4350fe37d285598ebe5ef9e3253ac2af12e3b35`.

L'utilisateur veut des services métier locaux sans compte fournisseur, pilotables
et observables par l'assistant pour tester et corriger le parcours complet.
L'IA intervient depuis cette session par le navigateur et les outils existants;
le laboratoire n'appelle aucune API de modèle et ne requiert aucune nouvelle clé.

## Parcours et responsabilités

- Une console web locale montre les messages fictifs, le contenu effectivement
  lu via MCP, la proposition, les décisions et la boîte destinataire calculée
  depuis le MIME enregistré par le fournisseur indépendant.
- Le vrai broker, OPA et le fournisseur HTTP simulé tournent en processus locaux.
  Les interactions agent passent par le SDK MCP officiel; sélection, revue,
  approbation, refus et révocation passent par le véritable socket humain.
- L'assistant pilote un parcours au navigateur et rédige la réponse à partir du
  message réellement retourné par MCP. Une campagne reproductible utilise un
  client MCP scripté; son rapport distingue ces deux modes d'intervention.
- L'opérateur de test peut jouer les deux rôles pour automatiser les cas. Cela
  teste le protocole d'approbation; ce n'est ni un consentement humain réel ni
  une preuve d'isolation entre comptes Linux. Aucune nouvelle permission n'est
  ajoutée au broker ou à ses quatre outils MCP.

## Implémentation bornée

Sous `pilots/codex_email/lab/` : supervision des processus et preuves, scénarios
avec assertions indépendantes, serveur de contrôle, interface HTML/CSS/JS et CLI
`serve` / `run`. Bibliothèque standard et dépendances déjà verrouillées du pilote.
Réutiliser le fournisseur de `tests/fixtures/provider_server.py`; ajouter au
besoin une option CLI pour son mode initial de panne, sans route administrative
exposée au fournisseur. Les sources métier et les locks restent inchangés.

La console est une surface d'opérateur authentifiée par un jeton éphémère propre,
distinct des jetons agent/fournisseur. Écoute loopback, vérification Host/Origin,
pas de CORS ouvert, entrées bornées, chemins/routes fixes et contenu rendu en
texte. Pas de HTML de message interprété. Aucun secret dans les états, journaux
de parcours ou preuves exportées. Les fichiers d'exécution privés restent dans
un dossier neuf hors du dépôt; on ne supprime ni ne réutilise un dossier existant.
Le jeton opérateur est remis via un fichier runtime privé (0600), jamais inclus
dans les assets publics ou une query URL. Le navigateur le reçoit explicitement
(champ de connexion ou fragment de lancement effacé), puis utilise un en-tête
Authorization. Il n'apparaît pas dans les journaux/export. Chaque mutation porte
l'identifiant de l'exécution affichée; une page obsolète reçoit un conflit.
Lancement, arrêt, nouvelle exécution et mutations sont sérialisés.

Chaque exécution conserve commandes sans secrets, événements, réponses MCP,
résultats, tentatives/effets indépendants et diagnostics utiles. Les arrêts
concernent seulement les processus créés par le laboratoire; nettoyage borné
de leurs groupes, y compris en échec de démarrage. La console reste disponible
après un échec de scénario et permet de relancer dans un nouvel état.

## Acceptation

1. Parcours navigateur assisté : lire via MCP, rédiger/proposer, observer zéro
   effet avant décision, approuver par le canal opérateur, observer un seul
   message destinataire dont les octets égalent ceux de la revue.
2. Campagne automatisée : approbation, refus, révocation, expiration réelle,
   replay, redémarrage avant décision, refus fournisseur, résultat incertain
   après effet et lecture hors délégation. Chaque cas produit un résultat
   explicite observé chez le fournisseur; les erreurs ne deviennent pas succès.
   Oracles fixés : accepté = `accepted` et 1 tentative/1 effet, octets du snapshot
   revu identiques au MIME enregistré; refus humain = `rejected`, 0/0; révocation
   ou expiration avant décision = `denied`, 0/0, contenu sensible masqué; refus
   fournisseur = `failed`, 1/0; déconnexion après effet = `unknown`, 1/1, inchangé
   après replay/redémarrage/nouvelle clé. Une lecture hors délégation exige une
   erreur MCP sans contenu interdit, après un contrôle positif; le journal du
   fournisseur d'envoi ne constitue pas l'oracle de cette lecture.
3. Les tests d'accès à la console rejettent une absence de jeton, une origine
   étrangère et une tentative de parcourir les fichiers; les données hostiles
   s'affichent inertes. Les erreurs de parcours restent diagnostiquables.
4. Suite complète du pilote verte, puis vérification du navigateur et revue
   indépendante des oracles et de la portée des preuves. Les tests existants
   ne sont répétés qu'après modification pertinente ou problème concret.

## Limites et livraison

Pas d'installation système, de nouvelle authentification fournisseur, de SMTP,
de Gmail, d'envoi réel, de téléchargement de modèle ni d'API payante. Le contrat
d'ingestion B reste proposé : les ressources fictives passent par `create_grant`
actuel, sans prétendre valider une ingestion ou Prompt Guard. La séparation
systemd/multi-UID reste une campagne ultérieure. Aucun commit/push de ce nouveau
lot n'est déduit de la publication précédente.

Livrer code exécutable, console locale maintenue disponible, commandes de reprise,
preuve actuelle distincte des rapports A/B/C et résultats de revue. L'assistant
recueille lui-même ses résultats et corrige les problèmes rencontrés.
