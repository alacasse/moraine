# Revue A et assertions de la campagne commune

2026-09-20. Revue ciblée du module embarqué, du vrai moteur et des tests. La baseline est conservée dans [l'archive avant revue](../../../experiments/results/before-review/manifest.json).

## Provenance et verdict

Le reviewer indépendant a vérifié les 18 fichiers du manifest A, confirmé la réutilisation apparitor/Cedar et relancé **37 tests avec succès** ([journal](../../../experiments/results/review-a/local-tests-loopback.txt)). Il a enregistré deux faiblesses des assertions communes avec des variantes volontairement défectueuses du serveur de test. Son tour a ensuite été interrompu par un filtre automatique signalant un possible risque cyber, avant la rédaction de son rapport final.

Le coordinateur, qui n'avait pas écrit l'implémentation A initiale, a complété la lecture et les vérifications de délai à partir des constats analogues de B/C. Ce document distingue donc les preuves du reviewer et ce complément local; il ne présente pas la revue interrompue comme achevée par cet agent.

**Deux défauts temporels de A et deux faiblesses d'assertion sont établis.** Les trois nouvelles instances de test temporel échouent sur A avant correction : [preuve avant correction](../../../experiments/results/root-a-regression-before.log). Les sources applicatives de la baseline restent disponibles dans l'archive.

## A-R1 — P1 : expiration pendant la persistance avant exécution

Dans la baseline, `gate.py:234-240` vérifie grant/review, puis `_transition(..., "executing", ...)` écrit et valide SQLite avant l'appel fournisseur. Une attente de verrou peut franchir l'échéance sans nouveau contrôle.

Deux régressions retiennent un vrai verrou SQLite sur la base jetable pendant une approbation, puis le libèrent après expiration : l'une pour le grant, l'autre pour l'âge de la revue avec un grant encore valide. Dans les deux cas, l'ancien code retourne `executed` avec un effet fournisseur. Le test attend `denied` et zéro effet, puis vérifie le replay après redémarrage.

Correction : contrôle des deux échéances après la transition durable, avant tout appel protégé. La réservation reste durable; une expiration connue avant envoi devient terminale et n'est pas réessayée. Ce contrôle concerne l'admission locale, pas une garantie atomique sur l'heure d'acceptation distante.

## A-R2 — P2 : seconde pièce jointe lue après expiration

La boucle `gate.py:168-173` de la baseline autorise l'ensemble de l'action avant préparation, lit toutes les pièces jointes, puis réévalue après préparation. Une première lecture lente peut donc être suivie d'une deuxième lecture après expiration.

La régression utilise deux références autorisées et le vrai fournisseur HTTP. Elle retarde le retour de la première lecture jusqu'après expiration, puis observe **deux lectures** sur la baseline, malgré l'état final `denied`. Ce refus final ne retire pas la lecture déjà effectuée.

Correction : vérifier l'heure avant chaque lecture. Le périmètre complet a déjà été autorisé et le verrou de cycle de vie empêche les modifications concurrentes du grant; seule l'heure avance dans cet intervalle. Le test attend une seule lecture et zéro effet.

## H-R1 — P2 : autorisation de création testée avec un corps invalide

Dans `run_campaign.py:359-369` de la baseline, les appels agent/other à `/grants` utilisent `{}`. Un refus de schéma peut satisfaire ce test même si le contrôle humain est absent. Correction : envoyer un grant entièrement valide sous chaque identité agent, exiger 401/403 et l'absence de grant/capability dans la réponse.

La [preuve du reviewer](../../../experiments/results/review-a/oracle-probes.json) montre que le test nommé `grant_creation_authority` passe avec une variante qui permet la création sous identité agent. La campagne entière de cette variante fait **29/30**, car une autre assertion détecte aussi son changement trop large des approbations. On ne prétend donc pas que toute la campagne ignorait cette variante.

## H-R2 — P2 : statut HTTP d'erreur masquant un faux état de succès

Les cas `provider_rejection` et `provider_unavailable` acceptaient tout statut HTTP >=400 même si le corps annonçait `state=executed`. La variante du reviewer retourne précisément HTTP 502 / `executed` sans effet et passe **30/30**. Preuves et script sont dans [review-a](../../../experiments/results/review-a/probe_oracles.py).

Correction : les cas de rejet/indisponibilité exigent maintenant un état `failed` ou `unknown`; l'acceptation suivie d'une perte de réponse exige `unknown` ou un succès réconcilié. Le statut HTTP seul ne suffit plus. Les contrôles des effets et du replay sont conservés.

## Apport et limites

Les tests de A exécutent les vraies dépendances et vérifient les effets. Le cas Cedar `Allow` accompagné d'une erreur est utile et distinct des règles métier. La qualité générale des tests n'empêche pas des lacunes dans les intervalles entre décision, persistance et IO : le défaut apparaît dans le cycle d'exécution custom.

L'interface embarquée réunit préparation, revue et exécution, mais l'identité reste une responsabilité du backend appelant. L'hôte HTTP ne prouve pas l'isolation d'un agent ayant accès au même processus ou utilisateur OS. Aucun élargissement du périmètre, nouvelle primitive cryptographique ou remaniement architectural n'est nécessaire pour ces corrections.

Les tests de correction et leur résultat final sont consignés dans [le journal A après correction](../../../experiments/results/root-a-regression-after.log) et [la synthèse de campagne](../COMPARISON.md). Les manifests avant revue ne sont pas remplacés.
