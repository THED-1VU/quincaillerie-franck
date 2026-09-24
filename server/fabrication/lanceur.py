"""Point d'entrée de l'exécutable Akuma.exe (cycle 28 : Akuma est la marque
de l'éditeur — voir ADDENDUM_CAHIER_DES_CHARGES.md).

Ce module est le SEUL fichier compilé par PyInstaller (voir
quincaillerie_franck.spec). Il ne contient aucune logique métier : il se
contente de démarrer le serveur (server/app/main.py, chantiers C2/C3/C11)
et d'ouvrir un navigateur dessus.

Architecture actée (voir RAPPORT AVANCEMENT/loop-state.md) : un seul code
applicatif web, livré comme un .exe Windows qui embarque ce serveur et ouvre
l'interface en plein écran — aucune installation de Python sur les postes,
double-clic comme l'application d'origine.

ÉTAT ACTUEL (cycle 30, correctif C0-A) : les écrans de la maquette sont
câblés sur ce serveur depuis le cycle 5 (chantiers C9/C10) et servis sous
/app par server/app/main.py (StaticFiles, html=True). Le navigateur ouvert
par ce lanceur pointe donc sur l'écran de connexion réel
(/app/connexion.html), jamais sur la documentation technique (/docs). Le
mode kiosque (plein écran) et l'outil de création du premier compte
responsable restent des chantiers C0 séparés, non traités ici.
"""

from __future__ import annotations

import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

# La console Windows par défaut (cp850/cp1252 selon la machine) affiche mal
# les caractères accentués de nos messages ("d�marr�" au lieu de "démarré").
# Purement cosmétique — le contenu réel des messages est correct — mais gênant
# pour un utilisateur non technicien : on force l'UTF-8 en sortie standard
# quand c'est possible (Python 3.7+, disponible en interactif comme figé).
for _flux in (sys.stdout, sys.stderr):
    if _flux is not None and hasattr(_flux, "reconfigure"):
        try:
            _flux.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001 — jamais bloquant, purement cosmétique
            pass

# --- Localiser server/ pour pouvoir importer "app" quel que soit le mode ---
# En développement, ce fichier est dans server/fabrication/ ; "app" est dans
# server/app/. Sous PyInstaller, tout est aplati dans le paquet : l'ajout au
# chemin est sans effet néfaste dans les deux cas.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn  # noqa: E402

from app.config import ErreurConfiguration, charger_config  # noqa: E402
from app.main import creer_application  # noqa: E402

HOTE = "127.0.0.1"

# Cycle 15 (C10) : le serveur écoute sur TOUTES les interfaces réseau
# (0.0.0.0), pas seulement la boucle locale — sinon un téléphone sur le
# même réseau ne peut techniquement pas l'atteindre, quelle que soit
# l'architecture par ailleurs (« ... via le réseau local ou un tunnel »,
# décision actée dès le cycle 0). Trouvé par exécution : jusqu'ici, HOTE
# servait À LA FOIS de socket d'écoute ET d'adresse ouverte dans le
# navigateur local — deux besoins différents, une seule constante était
# donc forcément fausse pour l'un des deux. Le navigateur local, lui,
# reste ouvert sur HOTE (127.0.0.1) : ouvrir un navigateur sur "0.0.0.0"
# ne fonctionne pas de façon fiable selon les navigateurs.
HOTE_ECOUTE = "0.0.0.0"
PORT_PAR_DEFAUT = 8000

# Écran d'accueil réel de l'application (C9/C10 câblés depuis le cycle 5,
# servis sous /app par server/app/main.py) : le double-clic sur l'exécutable
# doit ouvrir l'écran de connexion, jamais la documentation technique.
CHEMIN_A_OUVRIR = "/app/connexion.html"


def _adresse_lan() -> str | None:
    """Meilleure estimation de l'adresse IP de cette machine sur le réseau
    local, pour l'indiquer à l'utilisateur (accès depuis un téléphone).
    Astuce standard : ouvrir un socket UDP vers une adresse externe ne
    transmet AUCUNE donnée (UDP est sans connexion) — ça ne fait que
    demander au système quelle interface locale il choisirait pour y
    aller, sans jamais réellement l'atteindre ni exiger qu'elle réponde."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return None


def _pause_avant_fermeture() -> None:
    """Double-clic sur un .exe Windows : la fenêtre console se ferme
    instantanément à la fin du script, avant que l'utilisateur ait pu lire
    le message d'erreur. On la garde ouverte explicitement."""
    try:
        input("\nAppuyez sur Entrée pour fermer cette fenêtre...")
    except (EOFError, KeyboardInterrupt):
        pass


def _port_disponible(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((HOTE, port)) != 0


def _choisir_port() -> int:
    if _port_disponible(PORT_PAR_DEFAUT):
        return PORT_PAR_DEFAUT
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOTE, 0))
        return s.getsockname()[1]


_CHEMINS_NAVIGATEURS_KIOSQUE = (
    # Edge d'abord (livré avec Windows 10/11, donc présent sans rien
    # installer), puis Chrome. Chemins standard 64 et 32 bits.
    ("msedge", (
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    )),
    ("chrome", (
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    )),
)


def _navigateur_kiosque() -> tuple[str, str] | None:
    """Trouve Edge ou Chrome pour le mode kiosque (chantier C0, cycle 46).

    Retourne (exécutable, type) avec ``type`` valant ``"edge"`` ou
    ``"chrome"``, ou ``None`` si aucun des deux n'est installé (le repli
    est alors le navigateur par défaut, via ``webbrowser.open``).
    """
    for type_navigateur, chemins in _CHEMINS_NAVIGATEURS_KIOSQUE:
        trouve = shutil.which(type_navigateur)
        if trouve:
            return trouve, type_navigateur
        for chemin in chemins:
            if Path(chemin).is_file():
                return chemin, type_navigateur
    return None


def _ouvrir_navigateur_apres_demarrage(url: str) -> None:
    """Attend que le serveur réponde avant d'ouvrir l'interface — sinon
    l'utilisateur voit une page « ce site est inaccessible » pendant les
    quelques dizaines de millisecondes que prend le démarrage.

    Mode kiosque (cycle 46, décision du propriétaire) : Edge ou Chrome est
    lancé en ``--kiosk`` (plein écran, sans barre d'adresse), sans session
    ni onglets résiduels d'une utilisation précédente. Si aucun de ces deux
    navigateurs n'existe, repli sur le navigateur par défaut (comportement
    antérieur), jamais bloquant.
    """
    for _ in range(100):  # jusqu'à 10 s
        try:
            with socket.create_connection((HOTE, _PORT_COURANT[0]), timeout=0.2):
                break
        except OSError:
            time.sleep(0.1)

    navigateur = _navigateur_kiosque()
    if navigateur is None:
        webbrowser.open(url)
        return
    executable, type_navigateur = navigateur
    arguments = [
        executable,
        "--kiosk",
        url,
        "--no-first-run",
        "--no-default-browser-check",
    ]
    if type_navigateur == "edge":
        # Fenêtre kiosque véritablement plein écran sur Edge (le seul des
        # deux à accepter cette option dédiée).
        arguments.append("--edge-kiosk-type=fullscreen")
    subprocess.Popen(arguments)


_PORT_COURANT = [PORT_PAR_DEFAUT]


def main() -> int:
    print("Akuma — démarrage du serveur local...")

    try:
        config = charger_config()
    except ErreurConfiguration as exc:
        print(f"\nConfiguration invalide : {exc}")
        _pause_avant_fermeture()
        return 1

    port = _choisir_port()
    _PORT_COURANT[0] = port
    url = f"http://{HOTE}:{port}{CHEMIN_A_OUVRIR}"

    try:
        application = creer_application(config)
    except Exception as exc:  # noqa: BLE001 — on veut un message clair, pas une trace Python
        print(f"\nLe serveur n'a pas pu démarrer : {exc}")
        _pause_avant_fermeture()
        return 1

    threading.Thread(
        target=_ouvrir_navigateur_apres_demarrage, args=(url,), daemon=True
    ).start()

    print(f"Serveur démarré sur {HOTE}:{port}. Fermez cette fenêtre pour arrêter l'application.")
    adresse_lan = _adresse_lan()
    if adresse_lan:
        print(
            f"Depuis un téléphone sur le MÊME réseau (Wi-Fi) : "
            f"http://{adresse_lan}:{port}{CHEMIN_A_OUVRIR}"
        )
        print(
            "Si le téléphone n'y arrive pas, vérifiez le pare-feu Windows "
            "(profil réseau « privé », autoriser Python/uvicorn en entrée)."
        )
    try:
        uvicorn.run(application, host=HOTE_ECOUTE, port=port, log_level="info")
    except KeyboardInterrupt:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
