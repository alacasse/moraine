# Organisation et maintenance documentaire

## Documents actifs et preuves datées

`README.md` et `AGENTS.md` à la racine sont les points d’entrée humain et agent.
La documentation maintenue est sous `docs/`, avec [un index](README.md),
[l’état courant](status.md), l’architecture, les guides, plans et recherches.
Les commandes d’un guide déplacé indiquent leur répertoire d’exécution réel;
le code reste sous `pilots/`, `qualification/` et `experiments/`.

Actualiser le guide du composant lorsqu’un comportement ou une commande change.
Un plan précise ce qui est accepté, proposé, livré ou restant à qualifier.
L’état du projet cite des validations datées; une modification de documentation
ne transforme pas leurs résultats en une nouvelle campagne. Les recherches
conservent leur date et leurs sources; vérifier ces dernières avant une nouvelle
décision dépendant de versions ou de services externes.

Les rapports, manifests, archives, traces et données de tests constituent des
preuves historiques sous `pilot-results/`, `experiments/results/` et les dossiers
`evidence/` des prototypes. Conserver leurs bytes, chemins consignés et résultats.
Pour une nouvelle validation, créer de nouveaux artefacts. Les sources du checkout
peuvent évoluer : un ancien manifeste décrit sa capture, pas l’arbre courant.
Les instructions d’une mission historique se lisent dans leur contexte daté.

## Déplacement des guides du 20 septembre 2026

Dix guides ont été déplacés sans laisser de copie active ni de redirection dans
les dossiers de code. Les références des documents maintenus ont été adaptées.
Les rapports historiques restent inchangés : un ancien lien de guide dans une
preuve peut nécessiter la correspondance ci-dessous.

| Ancien chemin | Guide maintenu |
| --- | --- |
| `pilots/codex_email/README.md` | [Pilote](pilot/README.md) |
| `pilots/codex_email/INTERFACE.md` | [Interfaces](pilot/interface.md) |
| `pilots/codex_email/PROVENANCE.md` | [Provenance](pilot/provenance.md) |
| `pilots/codex_email/RUNBOOK.md` | [Déploiement Linux](pilot/linux-deployment.md) |
| `pilots/codex_email/lab/README.md` | [Laboratoire](pilot/local-lab.md) |
| `qualification/email_inspection/README.md` | [Qualification](qualification/email-inspection.md) |
| `experiments/README.md` | [Campagnes expérimentales](experiments/running.md) |
| `experiments/a_embedded/README.md` | [Prototype A](experiments/a-embedded.md) |
| `experiments/b_broker/README.md` | [Prototype B](experiments/b-broker.md) |
| `experiments/c_capability/README.md` | [Prototype C](experiments/c-capability.md) |

La [capture avant migration](../pilot-results/documentation/20260920/source-before-docs.zip)
conserve les 37 documents actifs tels qu’ils étaient avant ce travail et les
sources supplémentaires décrites par le manifeste du laboratoire. Elle inclut
les versions non commitées des README qui n’étaient pas récupérables dans Git.
Les chemins internes de l’archive sont les chemins d’origine depuis la racine.

Le [registre de migration](../pilot-results/documentation/20260920/migration.json)
consigne les correspondances, empreintes avant/après, empreinte de l’archive et
contrôles des preuves préservées. Les manifests historiques ne sont pas réécrits
pour les faire correspondre aux nouvelles versions documentaires. Pour vérifier
le manifeste du laboratoire, lire ses anciennes sources depuis cette archive
et ses preuves depuis leurs emplacements historiques inchangés.

Le runner des expériences empreint les fichiers présents sous `experiments/`
et le contrat commun; après ce déplacement, il ne couvre plus les guides sortis
des dossiers de code. `experiments/snapshot.py` ajoute les Markdown sous
`docs/experiments/` à son archive. Employer cette capture si une future revue
expérimentale doit figer aussi ses guides et plans.

## Vérifier une mise à jour

Vérifier les liens et ancres internes depuis l’emplacement final du document,
les chemins de commandes et l’absence de références actives aux anciens guides.
Distinguer ces références des citations de chemins historiques dans une preuve,
un inventaire d’origine ou la table ci-dessus. Préserver les sources applicatives
lors d’une migration documentaire pure. Si un guide est décrit dans un manifeste
mais sa version n'est pas conservée par Git, en archiver les bytes avant édition.

Le [contrôle de cohérence après migration](../pilot-results/documentation/20260920-consistency/REPORT.md)
consigne les écarts corrigés entre état courant, plans, guides et recherches.
Sa capture préalable correspond aux 42 documents du registre de migration;
son manifeste décrit les versions corrigées. Le registre de migration reste
la preuve de son propre état daté, sans être réécrit après ces corrections.
