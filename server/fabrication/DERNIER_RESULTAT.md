# Dernier résultat d'exécution — chantier C0, cycle 4

Exécuté le **2026-09-12**, PyInstaller **6.11.1**, Python **3.13.3** (venv
`server/.venv/`).

Trace rejouable :

```powershell
.\server\fabrication\construire.ps1
```

---

## Ce qui a été prouvé, par exécution réelle

### 1. Construction

```
Construction terminee.
  Executable : ...\server\fabrication\dist\QuincaillerieFranck.exe
  Taille     : 17.9 Mo
```

Deux avertissements à la construction, **expliqués et confirmés inoffensifs
par exécution** (pas par hypothèse) :

```
WARNING: Hidden import "_cffi_backend" not found!
WARNING: Hidden import "psycopg_binary._uuid" not found!
```

- `_cffi_backend` : provient du hook communautaire `hook-bcrypt.py`
  (`_pyinstaller_hooks_contrib`), écrit pour d'anciennes versions de
  `bcrypt` basées sur `cffi`. **bcrypt 4.2.1** (celui utilisé ici) est basé
  sur une extension **Rust**, pas `cffi` : ce module n'existe simplement pas
  dans cette version, et n'est jamais nécessaire.
- `psycopg_binary._uuid` : sous-module non trouvé par nom exact, sans
  conséquence observée dans aucun des tests ci-dessous (le projet n'a pas de
  colonne de type UUID).

### 2. L'exécutable tourne sans Python installé sur le poste

Copié seul (avec `config.ini`) dans un dossier **totalement isolé**
(`C:\Users\USER\Desktop\test_fabrication_qf\`, sans aucun fichier du projet
à proximité) :

```
INFO:     Started server process [63160]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:49824 (Press CTRL+C to quit)
Ets Quincaillerie Franck — démarrage du serveur local...
Serveur démarré sur 127.0.0.1:49824. Fermez cette fenêtre pour arrêter l'application.
INFO:     127.0.0.1:60800 - "GET /docs HTTP/1.1" 200 OK
```

Le navigateur s'est ouvert automatiquement sur `/docs`.

### 3. Les dépendances compilées à risque fonctionnent réellement

Testées une à une, dans l'exécutable empaqueté (pas dans le venv de
développement) :

| Dépendance | Test | Résultat |
|---|---|---|
| `psycopg[binary]` | `GET /sante` (connexion PostgreSQL réelle) | `{"etat":"ok","base":"joignable"}` |
| `psycopg[binary]` | `POST /auth/connexion` (requête + fonction SQL) | `200`, jeton renvoyé |
| `bcrypt` | `POST /auth/changer-mot-de-passe` (hachage `$2a$`) | `204`, puis reconnexion avec le nouveau mot de passe → `200` |
| signature HMAC (`hashlib`/`hmac`, stdlib) | jeton de la connexion | vérifié valide par une route protégée |

### 4. Les garde-fous de sécurité (chantier C11) survivent à l'empaquetage

Testés directement dans l'exécutable, pas seulement en développement :

```
$ config.ini absent
Configuration invalide : Fichier de configuration introuvable : ...\config.ini.
Copiez config.example.ini vers config.ini et renseignez les valeurs.

$ config.ini avec user = postgres
Configuration invalide : Configuration refusée : l'application ne doit jamais
se connecter avec le compte superutilisateur 'postgres'. Utilisez le rôle
applicatif qf_app (voir db/outils/definir_mot_de_passe_app.sql).
```

### 5. Résolution du chemin de configuration

`config.ini` est cherché **à côté de l'exécutable réel**, jamais dans le
dossier temporaire d'extraction de PyInstaller — vérifié en lançant l'exe
depuis trois emplacements différents (le dossier de fabrication, un dossier
isolé sur le Bureau, et une seconde fois après reconstruction), chaque fois
avec le `config.ini` de cet emplacement précis.

---

## Piège rencontré et corrigé — nommage du dossier source

Le dossier de fabrication s'appelait initialement `server/build/`. Or
`.gitignore` exclut tout dossier nommé `build/` (artefact de compilation
générique, réutilisé dans plusieurs langages) : **Git ignorait aussi mes
fichiers sources** (`lanceur.py`, le `.spec`, `construire.ps1`), sans
qu'aucun message d'erreur ne le signale — un `git status` bien intentionné
ne les aurait simplement jamais montrés.

Détecté par exécution (`git check-ignore -v`), pas par relecture. Corrigé en
renommant le dossier source en `server/fabrication/`, tout en conservant les
noms `dist/` et `build/` pour les **sous-dossiers de sortie** de PyInstaller
(`fabrication/dist/`, `fabrication/build/`) : ces noms correspondent
exactement aux règles génériques déjà existantes, donc aucune nouvelle
entrée `.gitignore` n'a été nécessaire.

```
git check-ignore -v server/build/lanceur.py
  .gitignore:8:build/   server/build/lanceur.py     <- AVANT : ignoré à tort

git add -A -n server/fabrication/
  add 'server/fabrication/construire.ps1'
  add 'server/fabrication/lanceur.py'
  add 'server/fabrication/quincaillerie_franck.spec'
  (aucun fichier de fabrication/dist/ ou fabrication/build/ proposé)   <- APRÈS : correct
```

---

## Ce que ce cycle NE couvre PAS (documenté, pas oublié)

- **Aucun écran réel n'est encore servi.** `/docs` est un placeholder : la
  maquette du cycle 1 n'est pas câblée sur ce serveur (chantiers C9/C10).
  Le mécanisme de lancement (choix de port, attente du démarrage, ouverture
  du navigateur) ne changera pas quand ce sera fait — seule la constante
  `CHEMIN_A_OUVRIR` dans `lanceur.py` changera.
- **Pas de mode kiosque activé.** Le navigateur s'ouvre en fenêtre normale.
  Le passage en plein écran (`--kiosk` pour Chrome/Edge) n'a de sens qu'une
  fois un vrai écran à afficher — prématuré tant que C9/C10 n'est pas fait.
- **Pas d'outil de création du premier compte responsable** (l'équivalent de
  l'ancien `CreerCompteResponsable.exe`). Le cahier des charges §7 le liste
  comme un second livrable distinct ; il reste à construire dans un cycle
  ultérieur — documenté dans `RAPPORT AVANCEMENT/loop-state.md`.
- **Pas de CI automatisée.** Le build est reproductible et documenté, mais
  pas encore déclenché automatiquement (GitHub Actions ou équivalent) à
  chaque changement.
