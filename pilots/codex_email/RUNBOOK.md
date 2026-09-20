# Préparer puis qualifier une installation Linux séparée

Ce lot prépare **le fournisseur simulé uniquement**. Rien dans ce document n’est
une preuve que l’installation est effectuée. Création des comptes, installation,
authentification Codex et comptes email demandent leur étape autorisée distincte.
Le [plan A](../../docs/plans/linux-isolation-preparation.md) et son
[rapport](../../pilot-results/parallel-workstreams/A/REPORT.md) délimitent les preuves.

## Contrat d’installation à réaliser par l’administrateur

| Chemin / identité | Propriétaire, modes et usage |
|---|---|
| `moraine-service` | Compte système sans shell interactif, aucun privilège; groupe primaire `moraine-human` pour le socket |
| `moraine-agent` | Compte distinct, pas membre de `moraine-human`, aucun sudo/Docker/pont vers la session humaine |
| Humain désigné | UID distinct du service et de l’agent, membre de `moraine-human`; UID fixé dans l’unité |
| Pair témoin | UID distinct, membre du groupe humain mais non habilité; seulement pour la sonde négative future |
| `/opt/moraine-pilot` et ancêtres | Administrateur (`root`), aucun droit d’écriture groupe/autres; copie figée du pilote, dépendances installées sans editable, OPA épinglé |
| `/etc/moraine-pilot/config.json` | `root:root`, 0644; exactement agent/owner/account, aucune URL arbitraire ni secret |
| `/etc/moraine-pilot/secrets` | `moraine-service:moraine-human`, 0700, parent `/etc/moraine-pilot` root 0755 |
| `secrets/{agent-token,provider-token}` | Service, 0600, valeurs distinctes; copie du seul jeton agent dans son home privé, jamais jeton fournisseur |
| `/var/lib/moraine-pilot` | Service, 0700; SQLite/blobs/WAL protégés, un broker, stockage local |
| `/run/moraine-pilot` | Service:groupe humain, 0750, créé par systemd; humain peut traverser mais pas créer/supprimer |
| `human.sock` / `human.sock.lock` | Service:groupe humain, 0660 / 0600; lock stable, ne jamais le supprimer pendant un processus actif |
| `/run/moraine-pilot/opa` | Service, 0700; OPA crée un sous-dossier aléatoire 0700 avec socket interne et token 0600; mode du socket à relever |

Les ACL doivent être absentes ou auditées : les modes seuls ne suffisent pas.
Vérifier `getfacl`, `namei -l`, UID/GID effectifs et règles SELinux sans désactiver
la protection de la machine. Aucun humain/agent ne peut modifier les parents.
Le socket OPA est protégé par ses parents 0700; son mode vient de l’umask
(typiquement 0700 sous l’unité), il n’est pas annoncé 0600.
Le service est dans la frontière fiable : le groupe ouvre la connexion, mais
`SO_PEERCRED` vérifie toujours l’UID humain exact. Le service ne fait que `chown(-1,
gid)` vers un groupe qu’il possède, jamais vers l’UID humain.

## Préparer les fichiers hors service

Après autorisation d’installation, un administrateur copie le pilote revu vers
`/opt/moraine-pilot` (pas un lien vers un workspace). Construire le venv à son
emplacement final avec Python 3.14 et le lock fourni, par exemple `uv sync --frozen --python /usr/bin/python3.14
--no-managed-python --no-editable --no-dev`; aucun editable/PYTHONPATH/workspace ne doit rester dans
le chemin d’import. Employer les caches/dépendances vérifiés disponibles. Ne pas
lancer le setup réseau implicitement; obtenir les artefacts manquants séparément.
Conserver les locks et la version exacte des outils dans la preuve d’installation.
Adapter le chemin à un Python 3.14 administré hors `/home` et `/root` :
`ProtectHome=yes` masque ces emplacements, y compris un Python géré par uv.

Copier l’OPA vérifié dans `.tools/opa`, le rendre exécutable par le service (0755),
et vérifier son SHA-256 :
`66fa66f3b730b2fb086003863428b382b2898d343adb4b5dfab5598b4d739eed`.
Donner à root tout l’arbre, enlever l’écriture groupe/autres, conserver lecture et
traversée du code/venv par le service et l’humain. Les seuls liens de fichiers
acceptés pointent vers des fichiers administrés (ex. Python système); pas de lien
de répertoire sortant de l’installation (le lien venv standard `lib64 -> lib`
reste permis et sa destination est parcourue). Installer les secrets hors de cet arbre, sans les afficher ni les
passer en arguments. Le simulateur reçoit sa propre copie du jeton fournisseur
et conserve son oracle dans un dossier indépendant, inaccessible à l’agent.

Créer un manifeste SHA-256 **après** installation non editable et gel des fichiers,
depuis `/opt/moraine-pilot`, en tant qu’administrateur :

```sh
find . -type f ! -path './SHA256SUMS' -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS
chmod 0644 SHA256SUMS
/usr/bin/python3 -I deploy/verify_install.py /opt/moraine-pilot /etc/moraine-pilot/config.json
sha256sum --check --strict SHA256SUMS
```

Le manifeste couvre le contenu installé (code, politiques, venv, OPA); la vérification
d’ownership parcourt aussi les ancêtres et destinations des liens. La provenance
de la copie et du manifeste reste une responsabilité administrateur; un manifeste
créé depuis une source non revue ne constitue pas une validation de cette source.
Le contrôle ne protège pas contre root ni une compromission du noyau.

Copier `deploy/config.json` vers `/etc/moraine-pilot/config.json`. Rendre
`deploy/moraine-email.service.in` en remplaçant les deux marqueurs numériques
`@HUMAN_UID@` et `@HUMAN_GID@` par les identités vérifiées. Les noms service/groupe
restent ceux du tableau. Ne pas installer un modèle avec marqueurs non résolus.
L’URL du simulateur est fixée à `http://127.0.0.1:8099`; aucun support Gmail ici.
Faire vérifier le fichier rendu par `systemd-analyze verify`, puis examiner
`systemctl cat` après son installation autorisée. Ne pas activer au boot avant
qualification; `WantedBy` indique seulement la cible éventuelle.

`ProtectSystem=strict`, `ProtectHome`, les répertoires runtime/état, `UMask=0077`,
`NoNewPrivileges` et l’ensemble vide de capacités complètent les modes. L’unité
lance Python avec `-I`; elle ne prend ni code ni environnement Python de l’agent.
Un serveur simulé séparé doit déjà être disponible pour le parcours fonctionnel;
l’unité peut démarrer sans lui, les appels fournisseur échoueront prudemment.

## Cycle de vie et reprise

- Arrêt normal : le broker ferme les canaux et OPA, conserve l’état métier.
- OPA termine : le watchdog observe le processus, ferme le broker avec statut 1;
  les décisions échouent fermées. `Restart=on-failure` relance une unité entière.
  Un OPA bloqué mais vivant provoque des délais/refus de politique; le watchdog
  ne prétend pas détecter tous les blocages. Intervention opérateur si persistant.
- Broker tué par SIGKILL : Python ne nettoie rien. **Sans superviseur, OPA survit**,
  observation reproduite localement. `KillMode=control-group` et `SendSIGKILL=yes`
  doivent arrêter les enfants restants avant reprise; cette propriété attend la
  sonde sur l’installation réelle. `TimeoutStopSec=20` borne l’arrêt supervisé.
- Les échecs répétés sont bornés par `StartLimitBurst=3` en 60 secondes. Après
  correction administrative, inspecter les journaux expurgés et réarmer l’unité.
- Un démarrage garde son verrou socket jusqu’à fermeture. Il refuse un endpoint
  actif et récupère uniquement un socket service obsolète (`ECONNREFUSED`), sous
  parent contrôlé. Il ne supprime ni fichier normal, ni lien, ni socket étranger.
- systemd supprime le runtime à l’arrêt (`RuntimeDirectoryPreserve=no`). Sans
  superviseur, les anciens sous-dossiers OPA peuvent rester après SIGKILL : arrêter
  explicitement tous les processus avant nettoyage administratif, jamais effacer
  à l’aveugle un socket ou un verrou. Les tests nettoient leur groupe à part.
- Ne pas restaurer une ancienne base puis reprendre les envois. Une intention non
  résolue et `unknown` restent conservatrices, sans replay automatique. La reprise
  pendant dispatch est couverte par d’autres tests métier; nos SIGKILL sont hors
  dispatch et n’ajoutent pas de preuve à ce sujet.

## Sondes futures, explicitement opt-in

Les deux scripts sont fournis pour une installation fictive jetable après
approbation de l’étape système. Ils n’installent rien. Ils exigent Python Linux,
cgroup v2 pour la supervision et l’accès administrateur pour les signaux.

1. Relever PID broker via `systemctl show moraine-email.service -p MainPID`, puis
   PID OPA dans `systemd-cgls /system.slice/moraine-email.service` et vérifier
   `/proc/PID/exe`. Relever `id` pour service, agent, humain, témoin de groupe.
2. Dans **chaque vraie session distincte**, lancer la sonde suivante avec les
   valeurs réelles. Un administrateur peut utiliser `runuser -u COMPTE -- ...`
   pour un compte service; conserver les groupes réellement appliqués. Ne pas
   simuler une identité en changeant seulement `--expected-uid`.

```sh
python3 /opt/moraine-pilot/deploy/probe_identity.py \
  --confirm-installed-probe --role human --expected-uid UID_HUMAIN \
  --human-uid UID_HUMAIN --service-uid UID_SERVICE --human-gid GID_HUMAIN \
  --broker-pid PID_BROKER --opa-pid PID_OPA
```

Répéter avec `--role agent`, `service`, `group-peer` et leur `--expected-uid`.
Attendus : agent connexion refusée par le noyau; humain connecté, requête vide
refusée par validation; pair de groupe/service connecté mais UID non autorisé.
La requête `{}` n’exerce aucune opération métier. La sonde lit les permissions
et ouvre des fichiers sans en lire le contenu; une absence de fichier est un
échec, pas un succès de confidentialité. Conserver les sorties JSON expurgées.

3. Sur cette installation **simulée jetable seulement**, l’administrateur lance :

```sh
python3 /opt/moraine-pilot/deploy/probe_supervision.py \
  --allow-kill-and-restart-simulated-installation
```

La sonde tue le broker puis OPA, attend la reprise réelle de l’unité, et vérifie
que tous les anciens membres du cgroup ont disparu via PID + starttime. Elle
ne substitue pas une relance manuelle à systemd; les signaux utilisent pidfd.
Une erreur arrête la qualification et exige inspection. Cette sonde vérifie le
retour du socket, pas le parcours MCP complet ni une reprise pendant dispatch.

4. Refaire le parcours MCP simulé et l’oracle fournisseur sous identités réelles;
   puis inventorier tous les outils/connexions de la future session Codex : pas
   de navigateur humain, D-Bus, X11/Wayland, keyring, SSH agent, Docker, sudo,
   home humain ou connecteur email distant. Les sondes fichier/socket ne couvrent
   pas cet inventaire. Aucun essai réel tant que l’étape 3 complète n’est validée.

Références primaires consultées : [Linux unix(7)](https://man7.org/linux/man-pages/man7/unix.7.html)
pour permissions et credentials;
[systemd.kill](https://github.com/systemd/systemd/blob/main/man/systemd.kill.xml)
pour le cgroup; [systemd.exec](https://github.com/systemd/systemd/blob/main/man/systemd.exec.xml)
pour runtime et confinement. La version installée reste à vérifier sur la cible.
