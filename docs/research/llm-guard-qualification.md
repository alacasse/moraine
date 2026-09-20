# LLM Guard — qualification documentaire pour l'ingestion email

Consulté le **20 septembre 2026**. Statut : **exploration, aucun choix ni essai**. Sources primaires ouvertes : dépôt, documentation officielle, fiche du modèle et métadonnées PyPI. Aucun paquet installé, aucun modèle téléchargé, aucun email traité. Complément à la [recherche sur l'inspection](email-content-inspection-sources.md).

## Maintenance et licence

Le dépôt `protectai/llm-guard` est **archivé depuis le 9 juillet 2026**. Son avertissement indique que le projet et les modèles associés ne sont plus développés ni maintenus. Les anciennes phrases du README annonçant des améliorations continues ne doivent pas masquer cet avertissement. [Dépôt officiel](https://github.com/protectai/llm-guard)

Le code est sous **MIT**; le modèle par défaut `protectai/deberta-v3-base-prompt-injection-v2` annonce **Apache-2.0** et son propre arrêt de maintenance. Il faut distinguer ces licences de celles des dépendances. [Licence du code](https://github.com/protectai/llm-guard/blob/main/LICENSE), [fiche du modèle](https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2)

## Ce que fait réellement `PromptInjection`

L'API documentée est `scanner.scan(prompt)`, avec un tuple nommé `(sanitized_prompt, is_valid, risk_score)`. Les emails figurent parmi les cas d'usage envisagés. [Documentation officielle](https://protectai.github.io/llm-guard/input_scanners/prompt_injection/)

**Le code retourne pourtant le texte original, y compris lorsqu'il détecte une injection.** Ce scanner classe; il ne retire ni ne réécrit les passages suspects. Le booléen et le score sont des observations à interpréter par l'application. Le constructeur utilise par défaut `V2_MODEL`, `threshold=0.92`, `MatchType.FULL` et `use_onnx=False`; l'exemple documentaire choisit explicitement un autre seuil. [Implémentation](https://github.com/protectai/llm-guard/blob/main/llm_guard/input_scanners/prompt_injection.py)

La configuration du modèle fixe `max_length=512` et `truncation=True`. D'autres stratégies découpent les phrases ou des segments, ou conservent les extrémités. **Implication pour Moraine :** le mode complet par défaut ne prouve pas l'inspection intégrale d'un long email; il faudrait qualifier une segmentation qui ne dissimule pas des zones non analysées. [Configuration et stratégies](https://github.com/protectai/llm-guard/blob/main/llm_guard/input_scanners/prompt_injection.py)

Le modèle par défaut est documenté pour **l'anglais**; sa fiche exclut les prompts non anglophones et la détection des jailbreaks, et signale des faux positifs sur les prompts système. Les performances publiées ne valident donc pas notre usage français/anglais. [Limites déclarées du modèle](https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2#limitations)

## Python et charge d'intégration

La version **0.3.16**, publiée le **19 mai 2025**, impose **Python `>=3.10,<3.13`**. **Python 3.14 est explicitement hors de cette plage**, pas seulement non testé selon une borne permissive. La matrice CI consultée couvre 3.10, 3.11 et 3.12. Cela ne démontre pas qu'un portage serait impossible, mais il ne s'agirait plus d'une intégration officiellement déclarée compatible. [Métadonnées PyPI](https://pypi.org/project/llm-guard/), [matrice CI](https://github.com/protectai/llm-guard/blob/main/.github/workflows/test.yml)

Le paquet impose notamment `torch>=2.4.0`, `transformers==4.51.3`, NLTK, Presidio et d'autres scanners; les extras ONNX utilisent `optimum` épinglé. Ce n'est pas une simple fonction de nettoyage sans dépendances de modèles. Le chargeur appelle `from_pretrained` pour le tokenizer et les poids; leur disponibilité et un provisionnement contrôlé restent à traiter. [Dépendances](https://github.com/protectai/llm-guard/blob/main/pyproject.toml), [chargement des modèles](https://github.com/protectai/llm-guard/blob/main/llm_guard/transformers_helpers.py)

## Appréciation pour Moraine — analyse, pas décision d'adoption

Trois obstacles empêchent de traiter cette piste comme un composant immédiatement qualifié : maintenance arrêtée, modèle par défaut inadapté au français, et plage Python excluant 3.14. Le mécanisme de scanners reste une référence lisible, mais l'adopter exigerait d'assumer un maintien propre ou une autre distribution, et de qualifier un autre modèle. Aucune alternative de ce type n'est validée ici.

**Question de qualification concrète :** quel bénéfice apporte l'enveloppe LLM Guard à notre ingestion, comparée à un appel direct à un classifieur bilingue maintenu, après prise en compte de son portage Python, de ses dépendances et de la couverture des messages longs ? L'assainissement MIME/HTML et le contrôle des permissions resteraient des responsabilités distinctes dans les deux cas.
