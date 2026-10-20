# Preuve de simulation d'installation — cycle 64 (2026-10-20)

Ce document rapporte l'exécution réelle de la procédure
[`README.md`](README.md) dans un **dossier temporaire isolé**
(`%TEMP%\akuma_c64_sim`), avec un PostgreSQL indépendant du développement
(port 5434). Aucune donnée réelle, aucun poste de production : c'est la
recette du jour J rejouée contre du vide, pour prouver que la liste de
fichiers et les commandes du dossier suffisent.

## A. Arborescence reconstituée (étape 1 du dossier)

| Élément copié | Preuve |
|---|---|
| `Akuma.exe` (depuis `server\fabrication\dist\`) | 30 209 765 octets présent |
| `config.example.ini` | présent |
| `db\migrations\` | **100 fichiers** `.sql` (50 migrations + 50 inverses) |
| `db\outils\` | scripts `.ps1` complets |
| `QuincaillerieFranck_Test\creation_base_donnees.sql` | présent |
| `_pgdev\pgsql\` | **912 Mio** (robocopy, débit 37,6 Mo/s) |

## B. PostgreSQL propre à la simulation (étapes 2–3)

- `initdb` sur `_pgdev\data` de la copie (locale `C`, UTF8,
  `--auth-host=scram-sha-256`), mot de passe propre au test ;
- démarrage `pg_ctl -o "-p 5434 -c listen_addresses=127.0.0.1" -w` ;
- `pg_isready -p 5434` → **`127.0.0.1:5434 - accepting connections`**.
- (Le service Windows de l'étape 3 n'est pas applicable dans une
  simulation — script déjà prouvé au cycle 28 ; rien d'autre ne change.)

## C. Base, schéma, migrations (étape 4)

1. `CREATE DATABASE quincaillerie_sim;` → OK.
2. `creation_base_donnees.sql` avec `ON_ERROR_STOP=1` → **SCHEMA_OK**.
3. **`migrer.ps1 appliquer` exécuté depuis la copie simulée**
   (`db\outils\migrer.ps1` du dossier `%TEMP%`) → **exit 0, 50 fichiers
   appliqués**, liste finale `schema_migrations` : versions 000→049,
   **49 lignes** (le numéro 040 couvre deux fichiers distincts).

### C.1 `migrer.ps1` — équivalence prouvée avec `migrer.sh`

Comparaison directe, même séquence (schéma → appliquer → compter →
annuler → compter), base jetable distincte par outil :

| Étape | Tables | Vues | Routines | Migrations |
|---|---|---|---|---|
| `migrer.ps1 appliquer` | 34 | 3 | 118 | 49 |
| `migrer.sh   appliquer` | **34** | **3** | **118** | **49** |
| `migrer.ps1 annuler`    | 14 | 0 | 67 | (table retirée) |
| `migrer.sh   annuler`   | **14** | **0** | **67** | — |

Résultats **strictement identiques** dans les deux sens. Les 67 routines
restantes après annulation sont exclusivement les objets des extensions
`pgcrypto` et `pg_trgm` (`armor`, `crypt`, `pgp_*`, `similarity*`,
`gtrgm_*`…) — les migrations inverses ne font pas `DROP EXTENSION`, ce qui
est voulu ; tout le code applicatif (51 fonctions) est bien retiré.
Référence de comparaison : base ne contenant que le schéma d'origine
(14 tables, 0 vue, 0 routine).

Deux défauts ont été trouvés par l'exécution et corrigés dans `migrer.ps1`
(avant d'être validés) :
1. `-Filter '[0-9][0-9][0-9]_*.sql'` de `Get-ChildItem` ne retourne **rien**
   (le filtre Win32 ne supporte pas les classes de caractères répétées) →
   filtrage par regex (`^[0-9]{3}_` puis exclusion des `*_inverse.sql`) ;
2. l'ordre schéma-d'abord-migrations-ensuite est obligatoire : appliqué seul,
   `001_contraintes_domaine.sql` échoue (`relation « utilisateurs » does
   not exist`) — le dossier l'exige dans cet ordre et la checklist B4–B6 le
   vérifie.

## D. Configuration et premier compte (étapes 5–6)

- Mot de passe du rôle `qf_app` posé par `db\outils\definir_mot_de_passe_app.sql`
  (`-v mdp=…`) → *« Mot de passe de qf_app défini »* ;
- `config.ini` écrit à côté de l'exe (host 127.0.0.1, port **5434**, dbname
  `quincaillerie_sim`, user `qf_app`, `secret_key` 64 hex aléatoires) ;
- `creer_compte_responsable.ps1 -ConfigIni …\config.ini` (mode automatisé)
  → **« Compte responsable cree (id 1, identifiant : resp.sim). A la
  premiere connexion, le mot de passe devra etre change. »**

## E. Lancement de l'exe depuis le dossier simulé (étape 7)

`Akuma.exe --sans-navigateur` lancé **depuis la copie** (`%TEMP%`), sans
variable d'environnement particulière :

| Sonde | Résultat |
|---|---|
| `GET http://127.0.0.1:8000/sante` | `{"etat":"ok","base":"joignable"}` |
| `GET /app/connexion.html` | **200** |
| `POST /auth/connexion` (resp.sim) | jeton émis, `"role":"responsable"`, `"doit_changer_mot_de_passe":true` |

La chaîne complète tient donc de bout en bout : exe isolé → config.ini →
rôle `qf_app` → base migrée 000→049 → authentification réelle.

## F. Défaut de déploiement trouvé par la simulation — corrigé

`GET /exploitation/derniere-sauvegarde` (avec jeton responsable) a répondu :

```
"Aucun fichier d'état trouvé (C:\Users\USER\AppData\Local\Temp\_pgdev\
sauvegardes\dernier_etat_sauvegarde.json)"
```

Cause : `RACINE_DEPOT` dans `server/app/routes/exploitation.py` était
calculé en `Path(__file__).parent × 4` — valable dans l'arborescence source,
mais dans l'exe figé `__file__` vit dans le dossier temporaire d'extraction
PyInstaller, donc le défaut résolvait n'importe où. C'est exactement le
symptôme que le cycle 63 contournait par la variable
`QF_FICHIER_ETAT_SAUVEGARDE`.

Correction (cycle 64) : en mode figé, la racine par défaut devient le
**dossier de l'exécutable** ; la variable d'environnement reste disponible
comme surcharge. Correction re-prouvée après reconstruction de l'exe :

| Sonde (exe reconstruit, même dossier simulé, toujours sans variable d'env.) | Résultat |
|---|---|
| `GET /sante` | `{"etat":"ok","base":"joignable"}` |
| `GET /exploitation/derniere-sauvegarde` | `"Aucun fichier d'état trouvé (C:\Users\USER\AppData\Local\Temp\akuma_c64_sim\_pgdev\sauvegardes\dernier_etat_sauvegarde.json)"` — le chemin résolu est désormais **celui du déploiement** |

Avec l'arborescence du dossier d'installation (`_pgdev\sauvegardes` à côté
de l'exe) et le fichier d'état par défaut de `sauvegarder.ps1`, le voyant du
tableau de bord fonctionne **sans aucune variable d'environnement** —
conclusion du cycle 63 limitée aux exe construits avant ce correctif.

## G. Régression

- Suite pytest complète sur base jetable migrée + jeu d'essai : voir
  `loop-state.md` cycle 64 (résultat consigné au journal).

## H. Nettoyage

Base de simulation, processus, dossier `%TEMP%\akuma_c64_sim` et journaux
`_tmp_*` supprimés après constat des preuves. Bases jetables du parcours
(`quincaillerie_c64mig`, `quincaillerie_c64ann`, `quincaillerie_c64ref`,
`quincaillerie_c64bash`) supprimées après comptages.
