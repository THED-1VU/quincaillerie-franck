# Dernier résultat d'exécution — chantier C0, cycle 64

Exécuté le **2026-10-20**, PyInstaller **6.11.1**, Python **3.13.3**
(venv `server/.venv/` monté sur le lockfile haché
`server/requirements.txt` — FastAPI 0.141.1, starlette 1.7.0).

Trace rejouable :

```powershell
server\.venv\Scripts\python.exe -m pip install -r server\requirements.txt
powershell -NoProfile -ExecutionPolicy Bypass -File server\fabrication\construire.ps1
```

---

## Cycle 64 — reconstruction avec correctif voyant (2026-10-20)

Reconstruction après deux défauts trouvés PAR EXÉCUTION lors de la
simulation d'installation complète du dossier `INSTALLATION/` (dossier
isolé `%TEMP%\akuma_c64_sim`, base `quincaillerie_sim` sur le port 5434,
preuves dans `INSTALLATION/PREUVE_SIMULATION.md`) :

- **`server/app/routes/exploitation.py`** : la racine du dépôt était
  calculée `Path(__file__).parent × 4` — valide dans l'arbre source, mais
  sous PyInstaller (`sys.frozen`) elle résolvait vers `%TEMP%\_MEIPASS`…,
  donc `%TEMP%\_pgdev\sauvegardes\` au lieu du dossier réel. Le voyant
  « dernière sauvegarde » exigeait alors la variable
  `QF_FICHIER_ETAT_SAUVEGARDE` (contournement documenté au cycle 63).
  Correctif : `RACINE_DEPOT = Path(sys.executable).parent` quand
  l'application est figée, sinon l'arbre source comme avant.
- **`server/fabrication/construire.ps1`** : construction via
  `python -m PyInstaller` (le shim `pyinstaller.exe` du venv sort en
  code 1 sans aucune sortie — correctif du cycle 63, porté ici à
  l'identique pour une fusion propre).

Résultat : `Akuma.exe`, **30 200 586 octets (28,8 Mo)**.

Prouvé par exécution dans la simulation : l'exe reconstruit résout le
fichier d'état `_pgdev\sauvegardes\dernier_etat_sauvegarde.json` **à côté
de l'exécutable** et répond `{"configure": true, ...}` avec le contenu
réel du fichier, **sans aucune variable d'environnement** — l'exigence
`QF_FICHIER_ETAT_SAUVEGARDE` du cycle 63 tombe pour les exe ≥ cycle 64.
`GET /sante` → `{"etat":"ok","base":"joignable"}` ; connexion réelle
(`POST /connexion`, jeton obtenu). Régression : pytest **306/306**.

---

## Cycle 63 (2026-10-20)

## Ce qui a été prouvé, par exécution réelle

### 1. Construction

```
Construction terminee.
  Executable : ...\server\fabrication\dist\Akuma.exe
  Taille     : 28.8 Mo
```

Trois corrections préalables, toutes trouvées PAR EXÉCUTION :

- `quincaillerie_franck.spec` : `clients.html`, `comptes.html` et
  `declarations.html` (écrans livrés après la construction du cycle 53)
  manquaient aux `datas` — l'exécutable les servait en **404** alors que
  le serveur de développement les sert. Ajoutés ; règle inscrite en
  commentaire : toute nouvelle page rejoint cette liste en même temps
  que l'écran.
- `lanceur.py` : nouveau drapeau `--sans-navigateur` (campagnes de test
  et démarrage sans kiosque ; le double-clic garde le kiosque).
- `construire.ps1` : construction désormais via
  `python -m PyInstaller` — le shim `pyinstaller.exe` du venv est
  ressorti en code 1 SANS aucune sortie (constaté ce jour), message
  trompeur ; le module produit le journal complet.

### 2. Lancement réel de l'exécutable, environnement isolé

`Akuma.exe --sans-navigateur` lancé depuis `server/fabrication/dist/`
(`config.ini` de test à côté de l'exe, base dédiée `quincaillerie_c63`
migrée 000→049). `GET /sante` → `{"etat":"ok","base":"joignable"}` ;
`GET /app/clients.html`, `/app/comptes.html`, `/app/declarations.html`
→ **200** (404 avant le correctif du spec).

### 3. Campagne Playwright complète CONTRE L'EXÉCUTABLE

12 suites « serveur réel » (branche CI Playwright, cycle 62, corrigée)
contre l'exe sur le port 8000 et la base `quincaillerie_c63` :
**431/431 contrôles, 0 échec** — routes 62, câblage 94, vente 49,
stock 49, rapports 39, inventaire 17, ux 27, comptes 26, caisse 24,
rh 21, exploitation 12, échappement 11.

Constat honnête du premier passage : câblage 4 échecs + exploitation en
timeout + stock 1 échec. Diagnostic : le voyant « dernière sauvegarde »
lit le fichier d'état via `QF_FICHIER_ETAT_SAUVEGARDE` (mécanisme
documenté du cycle 22) ; non configuré au lancement, le défaut relatif
à la racine figée ne peut pas deviner le dossier de sauvegarde du
déploiement. Après configuration de la variable (relance de l'exe) :
**les 3 suites sont revenues 94/94, 12/12 et 49/49**. L'échec stock
initial était le race déjà atténué au cycle 62 (mention « quantités
décimales ») — passé au rejeu. Exigence de déploiement consignée :
l'installation réelle doit positionner `QF_FICHIER_ETAT_SAUVEGARDE`
vers le dossier de sauvegarde (voir `db/outils/GUIDE_SAUVEGARDE_RESTAURATION.md`).

### 4. Sauvegarde / restauration re-prouvées sur cet environnement (C12)

`sauvegarder.ps1` a produit un dump chiffré AES-256+HMAC
(`quincaillerie_c63_20261020_190355.dump.enc`, 358 000 o) avant d'être
interrompu ; `restaurer.ps1` a restauré ce dump vers une base NEUVE :
37 tables, **données identiques à la source** (49 migrations max 049,
mêmes comptes par table, mêmes totaux), relecture des rôles conforme.
Cause de l'interruption : mise en quarantaine de `sauvegarder.ps1` par
Kaspersky (faux positif `PDM:Trojan.Win32.Generic` — preuves et action
propriétaire dans `RAPPORT AVANCEMENT/loop-state.md`, cycle 63).
`restaurer.ps1` n'est pas détecté.

---

## Historique des constructions

| Date | Cycle | Exe | Taille | Changement |
|---|---|---|---|---|
| 2026-09-12 | 4 | QuincaillerieFranck.exe | 17,9 Mo | Premier paquet autonome (ouvrait `/docs`) |
| 2026-09-20 | 30 | Akuma.exe | 26,4 Mo | C0-A : ouvre `/app/connexion.html`, maquette embarquée |
| 2026-09-25 | 53 | Akuma.exe | 28,8 Mo | Kiosque + pile FastAPI/starlette à jour |
| **2026-10-20** | **63** | **Akuma.exe** | **28,8 Mo** | **3 écrans 404 corrigés (clients/comptes/declarations), `--sans-navigateur`, build via `python -m PyInstaller`, 12 suites Playwright 431/431 contre l'exe** |
| **2026-10-20** | **64** | **Akuma.exe** | **28,8 Mo** | **Voyant : racine figée → dossier de l'exe (fin de l'exigence `QF_FICHIER_ETAT_SAUVEGARDE`), vérifié en simulation d'installation complète** |
