# -*- mode: python ; coding: utf-8 -*-
"""
Fabrication de Akuma.exe (chantier C0, cycle 4, renommé cycle 28 : Akuma
est la marque de l'éditeur, "Ets Quincaillerie Franck" reste le nom du
client — voir ADDENDUM_CAHIER_DES_CHARGES.md).

Empaquette le lanceur (fabrication/lanceur.py) et le serveur (app/) en un seul
exécutable Windows autonome, sans installation de Python requise sur le
poste cible — conformément à l'architecture actée
(RAPPORT AVANCEMENT/loop-state.md) et au cahier des charges §5
("Exécutables Windows autonomes (PyInstaller)").

NE PAS lancer directement avec `pyinstaller` sans passer par
fabrication/construire.ps1 : ce script vérifie l'environnement et copie
config.example.ini à côté de l'exécutable produit.

Liste de hidden-imports : uvicorn et psycopg chargent certains de leurs
sous-modules dynamiquement (importlib), ce que l'analyse statique de
PyInstaller ne détecte pas seule. Cette liste a été établie PAR EXÉCUTION —
en construisant l'exécutable, en le lançant, et en ajoutant chaque module
manquant signalé par l'erreur réelle — pas par supposition. Voir
fabrication/DERNIER_RESULTAT.md pour le détail de cette démarche.
"""

import sys
from pathlib import Path

RACINE_SERVEUR = Path(SPECPATH).resolve().parent

DOSSIER_MAQUETTE = (RACINE_SERVEUR.parent / "maquette").resolve()

# Correctif C0-A (cycle 30) : la maquette est servie par le serveur sous /app
# (server/app/main.py, StaticFiles, html=True) — elle doit donc être EMBARQUÉE
# dans l'exécutable, sinon le double-clic ouvre l'écran de connexion... en
# 404 (constaté par exécution : datas=[] laissait /app introuvable en mode
# figé). Seuls les fichiers réellement servis sont embarqués : les écrans
# HTML, leurs CSS/JS, le favicon et les assets de la marque. Les artefacts de
# test (maquette/verification/ — dont node_modules — et maquette/captures/)
# restent volontairement hors du paquet.
FICHIERS_MAQUETTE = [
    "api.js",
    "cloture-caisse.html",
    "connexion.html",
    "donnees-simulees.js",
    "favicon.ico",
    "index.html",
    "inventaire.html",
    "rapports.html",
    "rh.html",
    "stock.html",
    "styles.css",
    "tableau-bord.html",
    "theme.css",
    "vente.html",
]

datas = (
    [(str(DOSSIER_MAQUETTE / nom), "maquette") for nom in FICHIERS_MAQUETTE]
    + [(str(DOSSIER_MAQUETTE / "assets"), "maquette/assets")]
)

HIDDEN_IMPORTS = [
    # uvicorn choisit sa boucle d'événements et ses protocoles par
    # importlib au démarrage — invisibles à l'analyse statique.
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    # Extension C de psycopg (paquet "psycopg-binary" installé séparément) :
    # importée dynamiquement par psycopg selon ce qui est disponible.
    "psycopg_binary",
]

# NOTE (établie par exécution) : "psycopg_binary._uuid" est signalé manquant
# à la construction, sans conséquence observée — connexion, authentification,
# hachage bcrypt et écritures en base fonctionnent tous correctement dans
# l'exécutable produit (voir fabrication/DERNIER_RESULTAT.md). bcrypt 4.x utilise
# une extension Rust, pas cffi : un ancien hidden-import "_cffi_backend" a
# été retiré après vérification qu'il n'existe pas dans cette version.

a = Analysis(
    [str(RACINE_SERVEUR / "fabrication" / "lanceur.py")],
    pathex=[str(RACINE_SERVEUR)],
    binaries=[],
    datas=datas,
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Akuma",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # fenêtre visible : messages de démarrage, erreurs de config
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="akuma.ico",  # cycle 28 -- voir maquette/assets/akuma-monogram.png (source)
)
