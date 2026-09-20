# Contrat proposé d’ingestion des emails

Date : 20 septembre 2026. Lot B. **Plan proposé, revu techniquement;
aucune acceptation produit et aucune ingestion implémentée.** Base examinée :
`b63590cc02dbcb31859aeb683f4f71314beeb775`.

Autorité : [pilote §6 et §10](codex-mcp-email-pilot.md),
[note d’inspection](../research/email-content-inspection-sources.md).
La couche d’inspection et le rôle de Prompt Guard sont retenus. Les choix de
ce document — interface, politique, bornes, stockage et parcours humain —
restent des propositions. Aucun seuil, modèle, hébergement ou inspecteur
génératif n’est qualifié. Les valeurs numériques ci-dessous sont un profil
initial à tester, jamais des performances mesurées.

## 1. Écart au socle et invariant recherché

Dans [le broker actuel](../../pilots/codex_email/src/moraine_email/broker.py),
`create_grant` valide des ressources fournies par le canal humain puis insère
atomiquement grant, métadonnées et textes. `list_context` expose les métadonnées;
`read_context` vérifie grant, version et politique avant lecture du texte et
recontrôle l’activité avant retour. Le digest actuel couvre la ressource JSON,
pas des octets MIME originaux. [validate_grant](../../pilots/codex_email/src/moraine_email/models.py)
borne les corps à 32 Kio chacun et 128 Kio cumulés; les titres ne sont pas dans
ce cumul. Les versions sont actuellement fournies par le client humain.
Le fournisseur simulé actuel ne possède que le chemin d’envoi, pas la capture.

**Invariant proposé :** aucun texte externe ne sort par une surface agent sans
être couvert par une publication portant sur ses octets exacts, ses versions
et son périmètre inspecté. Cette publication ne remplace jamais le contrôle
de lecture. Les messages demeurent des données non fiables après inspection.
Les rapports et commentaires d’un inspecteur ne deviennent pas du contexte.

Trois notions indépendantes :

| Notion | Producteur et portée |
|---|---|
| Observation du détecteur | Score/classe par unité, statut et couverture; jamais une probabilité de sécurité ni un pouvoir |
| Décision de publication | Code déterministe versionné du service : `eligible`, `held`, `rejected`; porte sur une sélection figée, n’expose rien à elle seule |
| Autorisation | Sélection humaine pour capturer; puis grant et politique pour chaque lecture et proposition; approbation d’envoi distincte sur le MIME sortant exact |

## 2. Sources et surface couverte

Seul le propriétaire authentifié choisit une liste fermée de 1–5 IDs de
messages d’un compte configuré et au plus une note. Ni filtre vivant, ni fil
entier, ni URL, ni chemin arbitraire, ni pièce jointe ajoutée par l’agent.
L’inventaire humain borné conserve son audit propre; ses métadonnées ne sont
pas un résultat de `list_context`. Le futur adaptateur récupère les IDs exacts
après contrôle de la sélection. Il ne télécharge aucune pièce jointe par une
requête dédiée et ne suit aucun lien. Une réponse MIME peut transporter des
octets embarqués non retenus : le contrat ne promet pas zéro transit de ces octets.

La note est transmise en octets UTF-8 par le client humain, avec titre choisi;
le service n’ouvre pas son chemin d’origine. Le canal humain est authentifié,
mais le contenu de sa note reste soumis à l’inspection. Modifier une note,
un ID, le destinataire ou le périmètre exige une nouvelle sélection.

Le manifeste d’exposition, produit par le service, énumère **tous** les champs
externes rendus à l’agent : corps, sujet/titre, adresses, noms affichés s’ils
sont conservés, Message-ID et identifiants fournisseur/thread éventuellement
exposés. Proposition : retirer les IDs fournisseur/thread et Message-ID de
`list_context`; les garder privés pour la réponse et la traçabilité. Publier
référence opaque locale, version, digest, type, titre et adresses utiles
validées et inspectées. Tout futur champ externe doit rejoindre ce manifeste,
y compris previews et messages d’erreur; sinon il reste privé. Les références,
statuts et codes de motif générés par le service utilisent un vocabulaire fermé.

Inspection sémantique : corps décodé, métadonnées exposées et note, d’abord
avant rendu inerte, puis dans leur représentation publiée si différente.
Les mêmes octets peuvent partager une observation lorsqu’ils sont identiques.
Le manifeste décrit les unités et leurs limites; il inclut une représentation
composée des champs d’une ressource pour ne pas omettre leurs jonctions.
La segmentation doit couvrir l’intégralité de ces entrées. Elle ne prouve pas
la compréhension d’une attaque distribuée entre segments ou messages.

Le MIME complet subit une validation structurelle; ses parties HTML et pièces
jointes exclues ne sont pas déclarées sémantiquement inspectées. Elles ne sont
jamais publiées. `complete` signifie couverture complète du manifeste déclaré,
**pas inspection de tout l’email ni absence d’injection**. Une représentation
pré-transformée non analysable rend la couverture incomplète, même si le texte
publié paraît anodin.

## 3. Validation et transformations

Profil MIME initial volontairement étroit, à implémenter et tester :

- Accepter un `text/plain` unique, ou un arbre dont une seule branche de corps
  est sélectionnable sans ambiguïté. `multipart/alternative` est limité à un
  `text/plain` et un `text/html`, sans imbrication; seul le plain est publié.
  `multipart/mixed` est limité à ce corps et à des parties explicitement
  `attachment`; pas de seconde partie texte inline, message imbriqué ou archive
  à développer. Toute autre combinaison est refusée.
- Rejeter messages signés/chiffrés, HTML seul, charset absent avec octets non
  ASCII, charset inconnu, encodage invalide, structure/en-têtes ambigus ou
  dupliqués pour les champs interprétés. Parcourir les défauts de chaque partie,
  y compris ceux révélés au décodage; tout défaut signalé est bloquant dans v1.
  Un parsing réussi seul n’est pas l’oracle de conformité.
- Autoriser UTF-8 et US-ASCII stricts dans v1; transferts 7bit, 8bit, Base64 ou
  quoted-printable seulement après validation stricte sans réparation silencieuse.
  Limiter octets avant parsing puis après décodage; ne pas décoder les charges
  des pièces jointes exclues. Rejeter encodages de transfert inconnus.
- Décoder les en-têtes nécessaires de façon stricte; valider les adresses avec
  le sous-ensemble ASCII du pilote et les ambiguïtés From/Reply-To. Aucun
  destinataire n’est autorisé parce qu’il figure dans le message : l’humain
  confirme l’adresse exacte et le service la compare à la cible de réponse.

Transformations permises : décodages déclarés, dépliage d’en-têtes conforme,
normalisation CRLF/CR vers LF dans le corps, rendu explicite des contrôles
Unicode/terminal et échappement des antislashs pour lever l’ambiguïté des
séquences rendues. Garder une table de transformations et la correspondance
champs/plages entrée-sortie. Les en-têtes avec contrôles sont refusés comme
aujourd’hui. Aucun rendu HTML, Unicode NFKC, traduction, résumé, effacement de
citation, retrait d’impératifs ou « nettoyage d’injection » par réécriture.
Pas de chargement distant, exécution, terminal interprété ou ouverture de lien.

Conserver séparément bytes source, champs décodés et représentation publiée.
Le texte remis à l’agent est le texte rendu inerte, pas une copie brute lue par
un autre chemin. Une transformation modifiée produit une nouvelle version;
un contrôle rendu visible n’est pas une instruction éliminée. Toute perte
non prévue produit un refus, aucune troncature silencieuse. Une vue humaine
montre les écarts avec le même rendu inerte, sans exécuter les originaux.

## 4. Bornes et contrat interne proposé

Aucun format HTTP/JSON définitif ni framework de plugins. Une fonction interne
d’ingestion reçoit les captures déjà autorisées et un profil immuable; elle
retourne candidats et observations. Le broker possède sélection, publication
et autorisations. L’inspecteur reçoit uniquement des unités textuelles bornées
et leurs identifiants opaques; aucun grant modifiable, credential, boîte,
outil, accès fichier ou pouvoir réseau. Le déploiement reste à décider.

| Entrée ou sortie | Limite proposée et dépassement |
|---|---|
| Sélection | 1–5 messages + 1 note, IDs uniques; refus du lot entier si invalide |
| Source | 1 Mio de réponse MIME par message, 5 Mio cumulés, enveloppe transport également bornée; arrêt du flux dès dépassement |
| Complexité MIME | Profondeur 8, 32 parties, 100 en-têtes, 32 Kio d’en-têtes par message; refus avant expansion coûteuse |
| Texte décodé et publié | Chacun ≤32 Kio UTF-8 par ressource; métadonnées exposées ≤4 Kio par ressource, titre ≤512 caractères |
| Contexte total | ≤128 Kio UTF-8, corps **et** métadonnées exposées; vérifier avant et après transformation |
| Note transportée | ≤32 Kio source; jamais incluse sous forme de chemin |
| Inspecteur | Fenêtre de tokens déclarée par profil qualifié, sans troncature; ≤256 unités par ressource et ≤1 536 par lot, incluant les deux représentations et leurs recouvrements |
| Réponse inspecteur | Un seul résultat par unité attendue; score fini dans l’intervalle déclaré, classe fermée, aucun texte libre, IDs/digests concordants; doublon, extra ou omission = invalide |
| Rapport | ≤64 Kio par ressource et ≤384 Kio par sélection, serialization comprise; dépassement = échec, pas rapport tronqué |
| Temps et concurrence | Une seule tentative par sélection, budget total 30 s depuis lancement, récupération/parsing/inspection inclus; 1 analyse active et 4 sélections en attente par propriétaire; saturation = refus explicite |
| Durée de sélection | 5 min depuis création, sans prolongation par retry; expiration empêche finalisation même avec résultat favorable |

Un superviseur doit pouvoir arrêter le travail dépassant le budget; un simple
timeout de lecture renouvelé ou une future non annulable ne suffit pas. Ces
bornes pourront être ajustées après mesure, avec révision du profil; leur
compatibilité avec un modèle réel n’est pas présumée. Un profil sans version
et segmentation qualifiées ne peut autoriser des données réelles. Le faux
inspecteur utilise un profil marqué `synthetic`, réservé aux fixtures.

Objets conceptuels (noms indicatifs, clés exactes à figer lors d’un lot autorisé) :

| Objet | Informations obligatoires |
|---|---|
| Sélection | ID local, propriétaire/agent/compte, IDs exacts, note et digest, cible/destinataire, création/échéance, génération d’annulation et état |
| Capture | Clé compte + ID fournisseur privé, octets source immuables et SHA-256, instant de capture, origine; pour la note digest des octets et identité de l’import humain |
| Candidat | Référence/version allouées par service, digests source/extrait/publié, manifeste canonique d’exposition, transformations et versions parseur/rendu |
| Inspection | ID/tentative, digest des entrées, unités/plages attendues et observées, scores, `complete/partial/failed`, raison fermée, profil incluant détecteur/tokeniseur/segmentation/règles, horodatages |
| Publication | Sélection et génération, ensemble exact des candidats et rapports, décision déterministe/motif, révision de politique de publication, instant; digest canonique de cet ensemble |

Séparer révision de publication et révision Rego. Ni « aucun score disponible »
ni « minimum/max vide » ne peut produire `eligible`. Toute incohérence de schéma,
hash ou couverture invalide le résultat avant application de la politique.
Les scores restent des observations même lorsqu’ils valent exactement zéro.

## 5. Politique proposée et décision humaine

**Recommandation v1 : aucune dérogation de publication.** Publier un lot entier
seulement après validation, inspection complète et décision `eligible` obtenue
par un profil qualifié. Les seuils ne sont pas fixés ici : l’absence de seuil
qualifié bloque un déploiement réel. Une alerte bloque même si les autres
segments ont un score faible; pas de moyenne qui efface l’alerte.

| Situation | Décision et suite |
|---|---|
| Validation réussie, inspection complète sans alerte selon profil | `eligible`; finalisation possible après recontrôle de sélection et création du grant |
| Alerte d’une règle ou du détecteur, y compris désaccord | `held`; aucune publication; propriétaire peut consulter le rapport ou abandonner |
| Timeout, panne, réponse malformée, unité absente, analyse partielle, rapport trop grand | `held`; aucun secours brut; pas de nouvelle tentative dans cette sélection; un nouvel essai exige une nouvelle sélection humaine, soumise aux mêmes quotas et au marqueur d’alerte |
| MIME, taille ou fidélité non conformes | `rejected`; nouvelle source/sélection nécessaire |
| Révocation/annulation, expiration, profil retiré, stockage indisponible ou intégrité invalide | Interdire publication/lecture concernée; code sûr sans contenu; aucune reprise implicite |

Une sélection reste indivisible : si une seule ressource échoue, aucune de ses
ressources n’entre dans un grant. L’humain peut créer une autre sélection
fermée; le service ne supprime jamais silencieusement le message en alerte.
Des sélections successives conservent leurs tentatives respectives; aucune boucle « réessayer
jusqu’au score favorable ». Après alerte valide, un simple résultat favorable
sur la même entrée/profil ne l’efface pas. Conserver un marqueur d’alerte
bloquant par compte, identité source et digests des entrées/profil, commun à
toutes les sélections : recréer une sélection identique ou contourner le cache
ne rend pas le lot publiable. Seule une entrée effectivement différente ou une
révision explicitement qualifiée du profil permet une autre décision, avec
nouvelle sélection et liens vers l’alerte antérieure. Un simple changement de
numéro de profil ne suffit pas.

**Option non recommandée pour v1 : revue humaine autorisant une exception.**
Elle demanderait au minimum 2 verbes humains supplémentaires (ouvrir revue,
décider publier/refuser), 1 type de décision durable distinct des décisions
d’envoi, un nonce consommable, un digest du lot exact et une échéance. La vue
montrerait texte publié, changements, scores et limites de couverture sans
rendre les originaux actifs. L’humain autoriserait alors une divulgation à
Codex/OpenAI malgré une alerte, et non un envoi. L’approbation ultérieure du
MIME sortant resterait obligatoire et ne réparerait pas cette divulgation.

Cette option ajoute une seconde tâche de revue, ses états/péremption/replays,
un risque de fatigue et une décision de responsabilité produit. Elle ne
permettrait jamais de déroger à une autorisation révoquée, un MIME invalide ou
une provenance absente. Autoriser aussi une panne/couverture incomplète serait
une décision produit supplémentaire, pas une conséquence automatique d’une
exception sur alerte. Aucune de ces nouvelles surfaces n’est acquise.

## 6. Cycle, atomicité et révocation

Le socle n’a pas de grant en attente. Ajouter une **sélection temporaire**
autorise seulement les lectures fournisseur et l’analyse nécessaires, jamais
une lecture agent. Trois opérations humaines proposées : commencer sélection,
consulter son état/rapport protégé, annuler sélection. `create_grant` deviendrait
une finalisation par ID/digest de sélection inspectée et échéance du grant;
il ne recevrait plus des textes réputés publiables. La confirmation humaine
de délégation reste explicite. Aucun nouvel outil MCP d’inspection/publication.

Cycle : `selected → analyzing → eligible | held | rejected`, puis
`eligible → published` par finalisation humaine. `cancelled` et `expired` sont
terminaux depuis tout état prépublication. Aucune transition `held → analyzing` : une seule tentative, un seul ensemble
de rapports (≤384 Kio) et un seul budget de 30 s par sélection. Une consultation
ou une finalisation répétée ne relance pas l’analyse. Un nouvel essai commence
par une nouvelle sélection; les anciens rapports restent sous leur rétention
et le quota global les compte tous. Les retries réseau automatiques de capture
sont désactivés dans ce premier profil. Le grant publié a ensuite son
cycle indépendant de révocation/expiration. Le grant dure au plus 30 min depuis
finalisation, mais ne peut dépasser la validité restante de ses artefacts.

1. Sous verrou court et transaction, authentifier le propriétaire, figer
   sélection/génération et profil; réserver la tentative. Contrôler à nouveau
   avant chaque récupération ou reprise. Le corps fournisseur ne définit ni
   le compte, ni les droits, ni les URLs autorisées.
2. Relâcher le verrou pendant récupération/analyse bornée. Ne pas partager la
   connexion SQLite actuelle avec le worker. Le worker rend un résultat
   immuable au broker; seule la boucle propriétaire effectue les commits.
3. Au retour, relire l’état **courant** en base, l’échéance, la génération et le
   profil actif, pas une copie de grant conservée en mémoire. Un résultat tardif
   peut être audité comme abandonné mais ne ressuscite pas la sélection.
4. Lors de `create_grant`, refaire ces contrôles après acquisition du verrou
   SQLite; revalider digests/ensemble et décision. Insérer publication, grant et
   ressources ensemble, puis consommer la sélection, dans une seule transaction.
   Une finalisation répétée du même digest renvoie le même reçu/grant; un autre
   digest échoue. Aucun grant partiellement peuplé après crash.
5. À `list_context`, `read_context`, `propose_reply`, projection d’une demande
   et juste avant envoi, vérifier autorisation et admissibilité actuelle de la
   publication; après toute attente, recontrôler échéances et état. Une demande
   en attente ne contourne pas un retrait de publication. Les résultats d’envoi
   déjà terminaux restent historiques; leurs contenus peuvent être masqués.

Annulation acceptée pendant analyse invalide immédiatement la génération.
Une opération de récupération déjà partie ne peut être rappelée; le résultat
ne sort pas vers l’agent. Une révocation d’un grant déjà publié coupe ses
lectures, mais ne retire pas ce qui a déjà été transmis. Pour réinspecter on
crée une nouvelle sélection; révoquer l’ancien grant n’annule pas par magie
cette sélection distincte : le propriétaire doit pouvoir annuler celle-ci.
Le service affiche clairement les deux IDs et leurs portées.

La restitution agent est linéarisée au dernier contrôle du broker avant remise
au transport, sérialisé avec révocation. Une révocation acceptée après ce point
ne rappelle pas des octets déjà confiés au transport. Tester aussi expiration
pendant sérialisation; aucune prétention d’effacement dans Codex/OpenAI.
Au redémarrage, toute tentative `analyzing` est abandonnée, sans publication ni
réessai automatique. Un état persistant illisible bloque le chemin concerné.

## 7. Versions, cache et réinspection

Clé d’observation de cache : propriétaire/compte, identité et digest source,
digests des deux représentations et manifeste, versions parseur/rendu,
détecteur/tokeniseur/segmentation/règles et schéma de rapport. Ne partager ni
source, ni cache entre comptes. Une correspondance d’ID fournisseur seul est
insuffisante. L’empreinte lie les octets capturés, sans prétendre que le
fournisseur les certifie ou que son message courant n’a pas changé.

Réutiliser une observation complète et intègre n’accorde aucun accès : nouveau
contrôle de sélection, validité/rétention, puis nouvelle décision selon la
politique active. Une politique seule changée peut réutiliser les scores si
leurs entrées/profil restent compatibles, jamais l’ancienne décision. Un
changement de source, champ exposé, transformation ou détecteur invalide
l’observation. Les échecs et analyses partielles ne valent jamais cache favorable.
Le marqueur d’alerte du §5 est consulté même lors d’un cache manquant ou d’une
nouvelle capture identique; une observation favorable ne peut le remplacer.

Publication immutable : un grant continue de nommer son snapshot exact,
jamais « la dernière version ». La réinspection d’octets inchangés peut produire
un nouveau rapport, mais ne remplace pas le lien d’un ancien grant. Nouvelle
publication = nouvelle version locale et nouveau grant, même si texte identique.
Un registre de profils admissibles permet de retirer une version vulnérable :
les lectures, propositions et envois des grants concernés échouent jusqu’à
nouvelle sélection/publication. Pas de revalidation implicite d’un vieux grant.
Une simple mise à jour de profil ne retire pas les anciennes versions sans
événement explicite; cet événement et son effet doivent être atomiques.

Les anciennes ressources sans provenance d’inspection ne deviennent pas
« inspectées » par migration. Prévoir export des reçus nécessaires et refus de
publication/lecture de ces ressources dans le nouveau parcours; un réimport
explicite avec nouvelle sélection est nécessaire. Ne pas modifier les preuves
historiques ou annoncer le faux inspecteur comme une inspection réelle.

## 8. Persistance, confidentialité et rétention proposées

Trois familles durables nouvelles, dans le stockage protégé du broker :
(1) sélections/tentatives/annulations; (2) artefacts sources, extraits et rapports;
(3) publications avec liens et révisions. Il s’agit de familles conceptuelles,
pas d’une obligation de trois tables. Étendre les métadonnées des ressources
existantes et le contrôle de leur admissibilité. Aucun second service ou bus.

Les originaux peuvent contenir des pièces jointes embarquées exclues; leur
stockage reste un coût de confidentialité explicite. Proposition : conserver
les bytes capturés entiers pour fidélité/rejeu, sans téléchargement annexe,
avec accès propriétaire seulement. Rapports sans copie des segments, citations
ou justification générée; plages, digests, scores et motifs suffisent. Originaux,
extraits, snapshots, rapports et vues humaines restent sensibles, même sans
texte libre dans le rapport. Ne pas mettre de corps, sujet, adresse, MIME,
chemin local ou traceback contaminé dans journaux généraux ou erreurs MCP.

Proposition alignée sur l’hypothèse du pilote : supprimer contenu et rapports
au plus tard 7 jours après capture initiale, y compris tentatives échouées;
réutilisation du cache et réinspection ne repoussent pas cette date. Nettoyer
les temporaires à fin/abandon et au redémarrage. Expiration/révocation coupe
l’accès agent immédiatement, sans promettre un effacement physique immédiat.
Une échéance de purge dépassée bloque lecture/publication même si le balayage
n’a pas encore supprimé les bytes. La transaction de purge retire d’abord
l’admissibilité puis le contenu; ne jamais laisser un cache orphelin favorable.

Conserver des reçus minimaux jusqu’à clôture explicite du pilote : IDs opaques,
digests, états, révisions, instants, liens nécessaires aux barrières d’envoi.
Le marqueur d’alerte intersélections fait partie de ces reçus minimaux, sans
texte ni détail de score; la purge du rapport après sept jours ne le lève pas.
Il reste bloquant pour sa clé jusqu’au retrait explicite du profil ou à la
clôture du pilote (aucune nouvelle publication après clôture).
La durée « jusqu’à clôture » n’est pas une durée légale validée; le propriétaire
doit la confirmer avant des données réelles. Ne pas purger les tombstones
`unknown` de l’envoi pour faire disparaître un blocage. Prévoir WAL, fichiers
temporaires et sauvegardes dans la politique de purge; SQLite DELETE seul ne
prouve pas l’effacement sécurisé. Politique de sauvegarde et preuve de purge
restent à qualifier avant stockage réel, sans promesse ajoutée ici.

Budget logique maximal additionnel proposé : par sélection, 5 Mio source,
32 Kio note, ≤2 ×128 Kio représentations, 384 Kio rapports, soit <6 Mio hors
index/WAL/sauvegardes et snapshots d’envoi. Un quota global proposé de 256 Mio
pour ces nouvelles données refuse de nouvelles captures s’il est atteint;
ne pas évincer des preuves encore requises. Ce quota logique ne remplace pas
un budget disque et une surveillance de WAL à définir à l’implémentation.

## 9. Découpage de future implémentation

Chaque étape exigera une autorisation ultérieure; aucun code n’est produit ici.

| Sous-lot séquentiel | Changement et preuve attendue |
|---|---|
| B1 — Préparation déterministe | Nouveau module d’ingestion et fixtures MIME/note; profils, limites, manifestes, transforms et hashes; oracles de texte attendu écrits indépendamment du parseur |
| B2 — Faux inspecteur | Une interface interne fixe et faux résultats pilotés par tests; couverture/plages et validation stricte; aucune dépendance à un modèle ni au format d’évaluation C |
| B3 — Sélection et publication | Évolution broker/SQLite et create_grant; capture simulée distincte de l’envoi; transactions, annulation, reprise et migration; tests de concurrence avec barrières déterministes |
| B4 — Surfaces et rétention | CLI/socket humain : 3 opérations de sélection, finalisation existante adaptée; liste agent réduite, contrôles de projections/envoi, purge et quotas; tests bout en bout simulés |
| B5 — Qualification avant réel | Profil détecteur/version/segmentation/seuils, environnement/confidentialité, latence et corpus; accord produit et budget distincts avant téléchargement/exécution ou données réelles |

B1–B4 pourront être démontrés avec le profil synthétique. Cela ne suffit pas
pour activer l’ingestion réelle. B3/B4 touchent broker, modèles, politique,
transports et éventuellement locks : **réservés au coordinateur dans le
présent découpage**, besoins à planifier ultérieurement. Le lot A d’isolation
n’a pas à implémenter ces nouveaux verbes. Le lot C produit des artefacts
d’évaluation; leur schéma ne définit pas cette API. Un éventuel adaptateur
d’artefacts entre C et B5 sera explicite et limité, pas un système de plugins.

## 10. Acceptation et parcours démontrable futur

Ces vérifications sont **à exécuter dans un futur lot**, pas des résultats du B.
Les tests doivent observer des bytes retournés, accès protégés, état durable
et appels fournisseur; comparer uniquement un enum calculé serait insuffisant.

| Cas | Oracle mesurable |
|---|---|
| Message FR, message EN et note ordinaires | Avant finalisation, zéro ressource agent; ensuite texte/métadonnées exactement attendus et hashes recalculés indépendamment; deux messages + note seulement |
| Injection dans titre, adresse/nouveau nom affiché ou note | L’unité figure dans les entrées du faux inspecteur; alerte ⇒ zéro contenu via liste, lecture ou preview |
| Long texte, alerte en fin et à une jonction | Toutes plages attendues sont couvertes; fin/jonction présente; pas de score favorable si unité absente; ne pas conclure à la détection réelle |
| MIME ambigu, défaut dans partie enfant, HTML seul, charset invalide, dépassement d’une borne | Rejet et aucun snapshot publié; fixtures fixent attendu indépendamment du comportement tolérant du parseur |
| Contrôles, antislashs, citation légitime, texte accentué | Rendu inerte exact, pas de perte de sens silencieuse; transformations et digests correspondent aux octets; aucune ressource distante chargée |
| Résultat faux favorable pour une injection | Peut rendre le lot éligible, mais autre compte/version/ref/destinataire toujours refusés; zéro envoi sans approbation exacte |
| Panne, NaN, extra/doublon, mauvais digest, manque ou dépassement du rapport | `held`, aucun fallback brut et aucun grant partiel; absence de contenu externe dans erreurs |
| Annulation/expiration pendant capture/analyse ou attente SQLite | Barrière de test puis annulation acceptée, puis résultat libéré : aucune publication; relecture réelle de génération/échéance |
| Révocation avant restitution; retrait de profil avec demande pending | Aucun nouveau contenu/proposal/envoi; reçu terminal déjà acquis conservé, contenu sensible masqué |
| Cache : même ID avec source changée; version/règle changée; profil retiré | Aucun ancien verdict utilisé hors sa clé; lectures d’un ancien grant ne basculent jamais vers nouveau texte |
| Timeout puis consultation/finalisation répétée de la même sélection | Un seul appel d’analyse, aucun `held → analyzing`, budget 30 s non renouvelé et ≤384 Kio de rapports; nouvelle sélection explicitement nécessaire, quota global comptant les deux |
| Deux sélections avec mêmes entrées/profil, alerte puis faux avis favorable, avant/après purge du rapport | Marqueur durable conservé; seconde sélection bloquée même après redémarrage et sans cache; aucun nouveau grant |
| Crash avant/après commit publication, retry et reprise | Soit zéro grant, soit un seul grant complet identique; analyse interrompue abandonnée; aucun envoi déclenché |
| Purge/retention/quota | Accès refusé à échéance, cache invalidé; contenu/rapports retirés selon politique, tombstone unknown préservé; pas de revendication d’effacement physique |
| Ancien grant sans inspection | Aucun chemin ancien de create_grant/liste/lecture/projection ne contourne l’ingestion; migration explicitement testée |

Petit parcours reproductible : démarrer un fournisseur simulé avec journal
d’accès indépendant et un faux inspecteur à résultats fixés, préparer les trois
ressources fictives, vérifier l’invisibilité avant finalisation, publier puis
lire la sélection exacte. Rejouer avec une alerte dans la note et une unité
absente; vérifier zéro publication. Suspendre l’analyse par barrière, annuler,
puis libérer le résultat favorable; vérifier zéro contenu. Enfin injecter un
avis faux favorable, tenter de lire hors sélection et de changer le destinataire,
puis préparer la réponse autorisée : aucun effet avant l’approbation d’envoi.
Rapport distinct : preuves du contrat, non qualification de Prompt Guard.

## 11. Décision produit prioritaire et hypothèses

**Décision prioritaire proposée : adopter pour la première ingestion une
publication sans dérogation, bloquée en cas d’alerte, panne ou couverture
incomplète.** Recommandation : oui, pour borner ce premier parcours et éviter
d’ajouter immédiatement une deuxième approbation humaine sensible. Conséquence
assumée : des messages légitimes peuvent rester indisponibles; choisir une
autre sélection ou corriger/qualifier le profil prend du temps. Une revue
humaine d’exception serait un lot et une décision distincts (§5).

Autres hypothèses explicites, sans demande de décision simultanée : bornes et
durées proposées; rendu inerte sans réécriture; sélection durable et publication
atomique; conservation intégrale des captures pendant sept jours; quota logique;
retrait explicite des profils; refus des snapshots hérités; exécution du
détecteur et seuils encore à qualifier. Gmail reste une piste de futur connecteur.
Aucun inspecteur génératif, surface humaine d’exception ou téléchargement de
modèle n’est inclus. **La revue de ce plan ne vaut pas son acceptation.**
