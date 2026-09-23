# Fiche source — Confluence Cloud

Consultation publique le 21 septembre 2026. Aucun tenant ouvert ou créé.
Les alias ci-dessous sont une configuration proposée, pas des comptes réels.

| Prérequis | Valeur établie ou proposée | État dans cette session |
| --- | --- | --- |
| Site | Tenant Cloud exclusivement fictif, séparé des données personnelles et professionnelles | URL, propriétaire et autorisation absents |
| Édition | Standard suffit documentairement pour les permissions globales, d'espace et de contenu; Free ne permet pas de les personnaliser [C1], [C2] | Édition effective inconnue; D4 bloqué |
| O | Administrateur du site et des espaces de l'essai | Compte à désigner |
| U | Compte ordinaire distinct de O; aucune administration du site ou des espaces | Compte à désigner; un seul opérateur peut simuler les deux rôles |
| Espaces proposés | `MC26ATLAS` (D1/D2), `MC26BOREAL` (D3), `MC26RESERVE` (D4) | Aucun créé |
| Source | O voit D1–D4; U voit D1–D3; U n'a aucun accès à l'espace réservé | Droits attendus uniquement; pas de contrôle S0 |
| Clients fournisseurs | Une application OAuth dédiée par candidat; connexions A/B séparées admises | Aucune application ou connexion autorisée |
| Version | Confluence Cloud SaaS; relever version de page et date de lecture à S0 | Aucune version déployée relevée |
| Coût autorisé | Aucune nouvelle dépense | Aucun engagement pris |

**Durée et sortie d'essai : divergence documentaire à résoudre dans l'écran
d'activation.** La page tarifaire annonce sept jours pour Standard/Premium et
une inscription sans paiement [C3]. Le guide de changement depuis Free annonce
quatorze jours pour Standard et trente pour Premium, puis passage au forfait
payant [C2]. La FAQ d'achat précise un retour en Free à la fin des quatorze
jours Standard si aucune carte n'est ajoutée [C4]. Ne pas présumer lequel
s'applique au parcours qui sera désigné. Consigner la date de fin et le mode
de facturation effectivement affichés avant de confirmer. Aucun essai n'a
commencé et aucun délai de campagne externe ne court.

Le prix Standard extrait de la page est « $5.42 par utilisateur/mois », mais
le calculateur dépend de l'effectif et du cycle; devise et total pour O/U
ne sont pas établis. Ce chiffre n'est ni un devis ni un budget accepté [C3].

Pour D4, préférer **un espace entièrement fermé à U**, sans lien vers lui dans
D1–D3. La documentation explique qu'un simple contenu restreint à l'intérieur
d'un espace visible peut laisser apparaître un lien [C1]. Vérifier malgré tout
les résultats réels de recherche, liste et lecture directe sous U avant
d'attribuer un refus aux passerelles.

Après un éventuel essai autorisé : exporter les seules preuves nécessaires,
retirer les connexions puis les ressources consignées comme créées pour lui.
La désactivation d'un abonnement Standard/Premium en essai met fin à l'essai;
Free est désactivé immédiatement [C5]. Ne jamais désactiver un site préexistant
pour nettoyer quatre pages; faire approuver séparément une conservation du
nouveau site si souhaitée. Cette campagne n'a rien à désactiver.

## Première intervention nécessaire

Désigner un tenant fictif existant autorisé et les comptes O/U, ou autoriser
la création d'un tenant dédié avec deux identités désignées, zéro dépense et
aucune carte. Le périmètre initial est **S0 uniquement** : quatre pages et trois
espaces, droits U contrôlés, observation directe, puis suppression de ces
seules ressources. Une réponse limitée à S0 n'autorise pas Arcade, Workato,
leurs applications OAuth ou un appel de modèle.

## Sources officielles consultées

- [C1 — Structure des permissions](https://support.atlassian.com/confluence-cloud/docs/what-are-confluence-cloud-permissions-and-restrictions/).
- [C2 — Fonctions des éditions et changement de plan](https://support.atlassian.com/confluence-cloud/docs/learn-about-confluence-cloud-plans/).
- [C3 — Tarifs Confluence](https://www.atlassian.com/en/software/confluence/pricing).
- [C4 — FAQ achat et essais](https://www.atlassian.com/licensing/purchase-licensing).
- [C5 — Désactivation](https://support.atlassian.com/subscriptions-and-billing/docs/cancel-a-subscription/).

La première URL tarifaire sans `/en/` ne renvoyait aucun texte exploitable;
la variante anglaise a été lue. Une URL supposée de gestion des essais a
échoué : les sources C2/C4 ont ensuite été consultées. Aucun contenu de
communauté ou ancien manuel Confluence 5.x n'a servi à établir ces conditions.

[C1]: https://support.atlassian.com/confluence-cloud/docs/what-are-confluence-cloud-permissions-and-restrictions/
[C2]: https://support.atlassian.com/confluence-cloud/docs/learn-about-confluence-cloud-plans/
[C3]: https://www.atlassian.com/en/software/confluence/pricing
[C4]: https://www.atlassian.com/licensing/purchase-licensing
[C5]: https://support.atlassian.com/subscriptions-and-billing/docs/cancel-a-subscription/
