# Revue indépendante du plan d'accès agent

Date : **21 septembre 2026**. Relecteur : agent distinct
`/root/review_agent_access_plan`, lancé sans historique de la rédaction.
Mandat : revue en lecture seule du plan, confrontée au code et au périmètre
accepté; aucune implémentation ni campagne de tests.

## Version examinée

- [Plan capturé](PLAN.md), identique au
  [plan de travail](../../../docs/plans/agent-access-pilot.md) lors de la revue.
- SHA-256 : `5e4e31084cca21c85f566f85eada166bdf7cab9b2c8f4fb1585963c30756fc2d`.
- HEAD : `6e5a48372d74fa35d3709b041f22ce8a6e371348`.
- Sources : consignes applicables, racine documentaire `docs/`, contrats,
  architecture et sources du pilote. Les numéros de lignes ci-dessous
  désignent cette capture du plan et ce HEAD.

## Verdict du relecteur

**Prêt à implémenter, après autorisation du lot.** Aucun problème P1/P2
imposant une révision préalable n'a été trouvé. Deux précisions P3 sont à
fixer pendant l'implémentation. Ce verdict technique ne vaut pas autorisation
de développer, de configurer Codex ou de publier.

## P3 — Idempotence lors du regroupement de demandes

Plan, lignes 137–142 : même clé et même contenu doivent retrouver la même
demande; une demande du même périmètre déjà en attente ne doit pas créer une
seconde sollicitation.

Le socle associe une seule clé à chaque demande : contrainte
`UNIQUE(agent,idem)` dans
[broker.py](../../../pilots/codex_email/src/moraine_email/broker.py), lignes
58–65, et recherche par clé, lignes 270–276. Il ne fournit pas encore ce
regroupement.

Scénario : une demande existe sous A; une seconde conversation utilise B et
reçoit l'indication de cette demande en attente. Après refus de la première,
un retry B pourrait créer une nouvelle sollicitation si B n'a jamais été
associé au résultat initial.

Précision minimale suggérée : décider si la réponse consomme et rattache B à
la demande existante, ou retourne un conflit distinct sans accepter B.
Ajouter un cas vérifiant le retry après refus et redémarrage. Cela ne demande
pas une architecture supplémentaire.

## P3 — Expiration pendant la récupération

Plan, lignes 132–135 et 165–174 : un contrôle est demandé avant publication.
Les critères, lignes 213–224, couvrent l'expiration avant accord et celle du
grant publié, sans isoler l'intervalle entre accord et publication.

Le [broker actuel](../../../pilots/codex_email/src/moraine_email/broker.py),
lignes 342–367, recontrôle déjà les échéances après les attentes SQLite et
avant l'IO d'envoi. Le nouveau parcours doit rendre observable sa propre
frontière de publication.

Scénario : accord juste avant l'échéance, réponse fournisseur valide après
celle-ci. Fixer le résultat terminal, par exemple `approved/failed` avec
motif fermé d'expiration. Vérifier : une lecture fournisseur possible, zéro
grant, zéro ressource publiée, aucun nouvel appel après consultation ou
redémarrage. Cela complète une exigence présente dans le plan.

## Points cohérents et limites

Le relecteur juge cohérents l'identité stable entre conversations, le périmètre
figé et revu par digest/nonce, la récupération HTTP réelle, la publication
atomique, l'absence de retry implicite et le grant de lecture seule. La
distinction entre preuve scriptée et deux conversations Codex réelles est
explicite. Le plan ne qualifie pas l'ingestion réelle et n'impose pas une
infrastructure disproportionnée pour ce pilote.

Le relecteur n'a modifié aucun fichier, exécuté aucun test, lancé aucun service
ou changé de configuration. L'agent principal a conservé ce compte rendu et
la capture, puis contrôlé leurs liens et empreinte. Le plan de travail est
resté inchangé; les deux précisions ne sont pas encore intégrées.

La compatibilité effective avec Codex reste une preuve à produire lors du
lot. Cette revue statique ne constitue pas une validation d'exécution.
