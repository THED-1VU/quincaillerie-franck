# Dernier résultat d'exécution — chantier C0, cycle 53

Exécuté le **2026-09-25**, PyInstaller **6.11.1**, Python **3.13.3**
(venv `server/.venv/` monté sur le lockfile haché
`server/requirements.txt` — FastAPI **0.141.1**, starlette **1.7.0**,
pytest **9.1.1**).

Trace rejouable :

```powershell
server\.venv\Scripts\python.exe -m pip install -r server\requirements.txt
powershell -NoProfile -ExecutionPolicy Bypass -File server\fabrication\construire.ps1
```

---

## Ce qui a été prouvé, par exécution réelle

### 1. Construction

```
Construction terminee.
  Executable : ...\server\fabrication\dist\Akuma.exe
  Taille     : 28.8 Mo
```

### 2. Lancement réel de l'exécutable

`Akuma.exe` lancé depuis `server/fabrication/dist/` (config.ini de test à
côté de l'exe, base dédiée `quincaillerie_c0`). Le port 8000 étant occupé
par un processus parasite, le lanceur a choisi dynamiquement le port
**49322** — comportement prévu (`_choisir_port()`).

Journal HTTP réel du lanceur :

```
INFO: 127.0.0.1:50529 - "GET /app/connexion.html HTTP/1.1" 200 OK
INFO: 127.0.0.1:50529 - "GET /app/theme.css HTTP/1.1" 200 OK
INFO: 127.0.0.1:63376 - "GET /app/styles.css HTTP/1.1" 200 OK
INFO: 127.0.0.1:63124 - "GET /app/assets/akuma-logo.png HTTP/1.1" 200 OK
INFO: 127.0.0.1:54571 - "GET /app/api.js HTTP/1.1" 200 OK
INFO: 127.0.0.1:63124 - "GET /app/favicon.ico HTTP/1.1" 200 OK
```

`GET /sante` → `{"etat":"ok","base":"joignable"}`.

### 3. Mode kiosque (cycle 46) confirmé dans l'exécutable

Ligne de commande du processus Edge lancé par l'exécutable :

```
"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --kiosk http://127.0.0.1:49322/app/connexion.html --no-first-run --no-default-browser-check
```

### 4. Pile à jour embarquée

Le paquet embarque la montée majeure C11 (cycle 49) : FastAPI 0.141.1,
starlette 1.7.0 (pytest 9.1.1 : test uniquement), lockfile avec hachages
`server/requirements.txt`.

---

## Historique des constructions

| Date | Cycle | Exe | Taille | Changement |
|---|---|---|---|---|
| 2026-09-12 | 4 | QuincaillerieFranck.exe | 17,9 Mo | Premier paquet autonome (ouvrait `/docs`) |
| 2026-09-20 | 30 | Akuma.exe | 26,4 Mo | C0-A : ouvre `/app/connexion.html`, maquette embarquée |
| **2026-09-25** | **53** | **Akuma.exe** | **28,8 Mo** | **Kiosque + pile FastAPI/starlette à jour** |
