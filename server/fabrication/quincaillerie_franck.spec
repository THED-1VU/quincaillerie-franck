# -*- mode: python ; coding: utf-8 -*-
"""
Fabrication de QuincaillerieFranck.exe (chantier C0, cycle 4).

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
    datas=[],
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
    name="QuincaillerieFranck",
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
)
