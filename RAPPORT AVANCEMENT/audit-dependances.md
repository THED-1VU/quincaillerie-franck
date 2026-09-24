# Audit de dépendances et de TLS — 2026-09-24 (chantier C11, cycle 47)

Outil : `pip-audit 2.10.1` exécuté sur `server/requirements.txt` (lockfile
figé avec hachages, 36 paquets). Serveur : FastAPI 0.117.1, Python 3.13.

## Résultat global

| Paquet | Version audité | Advisories | Décision |
|---|---|---|---|
| `python-multipart` | 0.0.20 | PYSEC-2026-1852, 3036, 3037, 3038, 3039, 3040 | **CORRIGÉ** : monté à 0.0.31 |
| `starlette` | 0.48.0 | PYSEC-2026-2280, 2281 (fix = 1.1.0) | **Risque accepté, documenté** |
| `pytest` | 8.3.5 | PYSEC-2026-1845 (fix = 9.0.3) | **Risque accepté, documenté** |

## 1. `python-multipart` — corrigé

- **Pourquoi c'était réel** : la route de téléversement du logo
  (`server/app/routes/configuration.py`) utilise `UploadFile`/`File` ;
  `python-multipart` est la bibliothèque qui analyse ces envois. Les
  advisories visent des failles d'analyse de requêtes multipart.
- **Correctif** : `python-multipart==0.0.31` dans `requirements.in` +
  régénération du lockfile (`requirements.txt`, hachages inclus) +
  installation dans le venv local.
- **Preuve** : `pip-audit -r server/requirements.txt` ne signale plus
  `python-multipart` ; `pytest server/tests/test_configuration.py` **11/11**.

## 2. `starlette` — risque accepté (décision du propriétaire 2026-09-24)

- Les fixes demandent `starlette 1.1.0`, branche **majeure** (0.48 → 1.1)
  couplée à une migration FastAPI équivalente sur TOUT le serveur.
- **Impact** : aucune route n'est exposée sur Internet ; le serveur écoute
  sur le réseau local de la boutique et le risque est couvert par la posture
  réseau (voir §4). La migration majeure pendant le travail parallèle
  (point f) introduirait plus de risque qu'elle n'en retire.
- **Plan de traitement** : programmer la montée FastAPI/starlette dans un
  chantier dédié **après** la fusion du point f, avec rejeu complet
  (pytest + Playwright).

## 3. `pytest` — risque accepté (décision du propriétaire 2026-09-24)

- `pytest` est un outil de **test uniquement**, jamais embarqué dans
  l'exécutable ni exécuté sur les postes de la boutique.
- Le fix demanderait `pytest 9.0.3` (majeure) : migration de la suite,
  plugins, et risque de divergence avec les suites en cours côté point f.
- **Plan de traitement** : montée avec le même chantier dédié que
  FastAPI/starlette.

## 4. TLS — posture documentée

- Le serveur (`lanceur.py`, `uvicorn`) écoute en **HTTP** sur
  `127.0.0.1`/`0.0.0.0`, conformément à l'architecture locale de boutique.
- Les mots de passe ne transitent **jamais en clair hors du poste** :
  la vérification se fait par hachage bcrypt **dans PostgreSQL**, et les
  jetons de session sont signés (HMAC) et expirent.
- **Limite assumée** : si un tunnel vers l'extérieur est un jour utilisé,
  il faudra terminer TLS à la passerelle du tunnel (HTTPS) — le tunnel,
  pas le serveur local, porte alors le chiffrement. C'est la pratique
  standard pour ce type de déploiement ; elle est documentée ici comme
  décision de posture, pas comme manque de sécurité local.

## Conclusion

Le seul paquet exposé en production avec une vulnérabilité corrigeable sans
migration majeure (`python-multipart`) est **corrigé et prouvé**. Les deux
advisories restantes (starlette, pytest) sont des risques **acceptés,
documentés et planifiés**, conformément à la décision du propriétaire.
