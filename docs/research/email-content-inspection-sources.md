# Inspection et assainissement des emails — sources et pistes

Consulté le **20 septembre 2026**. Statut : **qualification documentaire, aucun essai**. Le cadrage retient désormais Prompt Guard comme une brique de la couche d'inspection et d'assainissement; sa variante/version, son intégration et les autres briques restent à qualifier. Les capacités ci-dessous proviennent des documentations primaires ouvertes; elles ne constituent pas une validation de sécurité pour Moraine. Les pages non versionnées décrivent l'état consulté, pas une version qualifiée.

Cette note soutient la couche d'ingestion du [plan du pilote email](../plans/codex-mcp-email-pilot.md). Elle distingue le décodage et l'assainissement technique, la détection d'injection et l'analyse générative. Aucune piste ne justifie à elle seule de déclarer un email « sûr ».

## Quatre pistes à qualifier

### 1. Bibliothèque standard Python `email` : parsing MIME et anomalies

`BytesParser` et `BytesFeedParser` construisent l'arbre du message MIME. Le parseur tolère aussi des messages non conformes et signale certaines anomalies dans `defects`; réussir le parsing ne signifie donc pas satisfaire une politique stricte d'acceptation. [Parseurs Python](https://docs.python.org/3/library/email.parser.html)

Les défauts appartiennent à la partie MIME concernée, pas nécessairement à la racine. Certains décodages Base64 corrigent ou ignorent des caractères tout en signalant que les octets obtenus peuvent être invalides. **Implication pour Moraine :** qualifier explicitement le parcours des parties, les encodages acceptés et les défauts entraînant un refus; ne pas accepter silencieusement une réparation. [Défauts de parsing et décodage](https://docs.python.org/3/library/email.errors.html)

### 2. DOMPurify : assainissement HTML, si ce format entre plus tard dans le périmètre

DOMPurify vise la prévention des XSS dans le HTML. Son modèle de menace exclut notamment la protection complète contre les chargements de ressources distantes et l'assainissement CSS. **Implication :** ce composant ne suffirait ni à empêcher tout suivi réseau, ni à détecter une consigne malveillante écrite en texte ordinaire. [Objectifs et limites officiels](https://github.com/cure53/DOMPurify/wiki/Security-Goals-%26-Threat-Model)

L'usage serveur dépend d'une implémentation DOM telle que `jsdom`, dont la version influence la sécurité. Modifier le balisage après assainissement peut invalider la protection. [Usage serveur et post-traitement](https://github.com/cure53/DOMPurify#running-dompurify-on-the-server)

Cette piste n'élargit pas le périmètre de la [proposition d'ingestion](../plans/email-ingestion-contract.md), qui prévoit de refuser les emails uniquement HTML. Le pilote actuel reçoit des textes fournis par le canal humain; il n'implémente ni parsing MIME entrant ni ce refus de format.

### 3. Meta Llama Prompt Guard 2 : classifieur spécialisé

Le modèle classe les tentatives explicites de remplacement des instructions; il ne réécrit pas l'email. Sa fenêtre est de **512 tokens**. Meta documente des évaluations en français et en anglais, ainsi que des limites face aux attaques adaptatives et aux distributions propres à une application. **Implication :** qualifier la segmentation des longs messages, les attaques réparties entre segments et les seuils sur notre corpus; les résultats publiés ne prouvent pas la couverture des emails Moraine. [Fiche officielle du modèle 86M](https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M)

### 4. LLM inspecteur avec instructions spécialisées : hypothèse d'analyse sémantique

Un modèle séparé peut examiner les entrées et produire une appréciation plus contextuelle. OWASP précise cependant qu'un LLM utilisé comme garde-fou reste lui-même exposé à l'injection et recommande de distinguer sa surface d'attaque de celle du modèle principal. **Des instructions spécialisées ne garantissent donc pas son immunité, ni l'absence de risque supplémentaire.** [Garde-fous fondés sur un modèle](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html#model-based-guardrails)

**Hypothèse pour Moraine, à évaluer :** commencer par un appel d'inspection borné, sans outils, credentials de messagerie, autres emails, mémoire partagée ni accès réseau pilotable par le modèle. Sa sortie structurée resterait une observation non fiable : une étiquette, une justification ou un résumé peut être erroné ou contaminé. Un schéma valide contrôle la forme, pas la vérité du verdict. L'inspecteur ne pourrait ni élargir le grant ni autoriser une action. Ces contraintes appliquent les principes d'isolation, de moindre privilège et de validation entre agents; elles ne constituent pas une preuve d'immunité. [Sécurité des agents et de leurs communications](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html#7-multi-agent-security)

## Questions de qualification avant une décision

Cette grille est une proposition d'évaluation pour Moraine, pas une liste de capacités déjà obtenues :

- **Licence et maintenance :** versions exactes du code et des poids, conditions d'usage, dépendances, avis de sécurité et procédure de mise à jour.
- **Pertinence du détecteur :** français, anglais et mélange des deux; faux positifs sur citations légitimes d'injections, faux négatifs sur attaques indirectes, obfusquées ou adaptées à notre tâche.
- **Contexte :** limites de tokens, segmentation et recouvrement, en-têtes et citations, comportement devant un dépassement; aucune troncature silencieuse présentée comme inspection complète.
- **Confidentialité :** exécution locale ou fournisseur externe, contenu réellement transmis, conservation, logs et autorité permettant cette divulgation supplémentaire.
- **Coût et robustesse :** latence, ressources, budgets, indisponibilité, timeout et réponse malformée; distinguer « non inspecté » de « aucune alerte ».
- **Fidélité :** suppressions, normalisations ou résumés qui changent le sens; provenance et transformations traçables, possibilité de revue humaine du contenu concerné.
- **Risque ajouté :** tenter de corrompre le verdict et la sortie de l'inspecteur, puis mesurer leur influence sur l'agent principal; comparer au traitement déterministe seul.

La question à trancher après qualification sera le gain mesuré de détection et de fidélité au regard des nouvelles dépendances et surfaces d'attaque. Le rôle de Prompt Guard dans la couche est retenu dans le plan; cette recherche ne qualifie encore aucune version ni intégration et n'autorise aucun traitement de messages réels.

## Qualification de la brique Prompt Guard — intégration à définir

**Prompt Guard est l'une des briques de la couche, avec Prompt Guard 2 86M comme premier candidat de version à évaluer.** La couche porte aussi validation, assainissement technique, politique de publication et traçabilité. La question de qualification du détecteur est : peut-on obtenir un signal utile sur des emails français/anglais sans produire de texte réécrit susceptible de transmettre l'injection, et sans bloquer trop de messages légitimes ?

La fiche Meta décrit une classification binaire, une fenêtre de 512 tokens et une base multilingue pour le 86M; elle signale une dégradation multilingue plus marquée pour le 22M et la possibilité d'attaques adaptatives. L'accès aux poids présentés sur Hugging Face est soumis à acceptation des conditions Llama 4. Leur accès et la compatibilité d'exécution restent à vérifier avant tout essai. [Fiche officielle et conditions d'accès](https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M)

L'exemple officiel retourne des scores, permet l'exécution CPU et propose un découpage des textes longs avec agrégation par maximum. Les fonctions de classification élémentaires activent la troncature : il faut qualifier le chemin utilisé et la couverture du message complet. Aucun coût ni temps CPU n'a été mesuré ici. [Code d'inférence officiel consulté](https://github.com/metainternal/llama-cookbook/blob/main/getting-started/responsible_ai/prompt_guard/inference.py)

**Analyse pour Moraine :** une sortie limitée à un score/une classe réduit la possibilité de réintroduire une consigne via un résumé ou une justification générée. Le classifieur peut néanmoins se tromper; son score n'est pas une autorisation. Cette piste couvre la détection, pas le parsing MIME, l'assainissement technique ou la fidélité d'une réécriture. Elle fournirait un point de comparaison pour décider ensuite si un inspecteur génératif apporte un gain.

Le [banc C](../qualification/email-inspection.md) fournit désormais un corpus
fictif et un évaluateur hors ligne. Aucun détecteur n'y a encore été exécuté;
l'essai de Prompt Guard et sa qualification restent à réaliser :

1. Partir du corpus fictif annoté livré et vérifier sa couverture : demandes ordinaires, citations légitimes de consignes suspectes, injections explicites/indirectes, français et anglais, messages longs avec attaque en fin ou entre deux segments. Compléter les cas manquants en conservant la séparation entre réglage des seuils et évaluation.
2. Vérifier que chaque partie du message est inspectée et mesurer les omissions liées au découpage; ne jamais présenter un message tronqué comme inspecté intégralement.
3. Mesurer faux positifs/faux négatifs, latence et mémoire; comparer au traitement technique seul. Ne pas transformer un score du modèle en probabilité de sécurité pour Moraine.
4. Décider à partir des cas ratés si ce signal vaut une alerte/revue, si un autre détecteur est nécessaire ou si l'analyse générative mérite un essai distinct. Les permissions restent indépendantes dans tous les cas.

**Alternative examinée : LLM Guard.** Le dépôt a été archivé le 9 juillet 2026; le README indique que le projet et les modèles associés ne sont plus maintenus. Cela le rend peu favorable comme nouvelle dépendance de sécurité, même si son code reste une référence utile. Voir la [qualification ciblée](llm-guard-qualification.md) et le [constat officiel](https://github.com/protectai/llm-guard).
