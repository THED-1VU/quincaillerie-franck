"""Point d'entrée de l'exécutable QuincaillerieFranck.exe.

Ce module est le SEUL fichier compilé par PyInstaller (voir
quincaillerie_franck.spec). Il ne contient aucune logique métier : il se
contente de démarrer le serveur (server/app/main.py, chantiers C2/C3/C11)
et d'ouvrir un navigateur dessus.

Architecture actée (voir RAPPORT AVANCEMENT/loop-state.md) : un seul code
applicatif web, livré comme un .exe Windows qui embarque ce serveur et ouvre
l'interface en plein écran — aucune installation de Python sur les postes,
double-clic comme l'application d'origine.

ÉTAT ACTUEL (cycle 4, chantier C0) : les écrans de la maquette (cycle 1) ne
sont pas encore câblés sur ce serveur (chantiers C9/C10, cycle ultérieur).
Le navigateur ouvert par ce lanceur pointe donc, pour l'instant, sur la
documentation interactive de l'API (/docs) — le seul « écran » que le
serveur sait réellement servir aujourd'hui. Une fois C9/C10 fait, seule la
constante URL_A_OUVRIR ci-dessous change ; le mécanisme de lancement, lui,
ne change pas.
"""

from __future__ import annotations

import socket
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

# Placeholder documenté ci-dessus — à remplacer par l'écran de connexion une
# fois C9/C10 fait.
CHEMIN_A_OUVRIR = "/docs"


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


def _ouvrir_navigateur_apres_demarrage(url: str) -> None:
    """Attend que le serveur réponde avant d'ouvrir le navigateur — sinon
    l'utilisateur voit une page « ce site est inaccessible » pendant les
    quelques dizaines de millisecondes que prend le démarrage."""
    for _ in range(100):  # jusqu'à 10 s
        try:
            with socket.create_connection((HOTE, _PORT_COURANT[0]), timeout=0.2):
                break
        except OSError:
            time.sleep(0.1)
    webbrowser.open(url)


_PORT_COURANT = [PORT_PAR_DEFAUT]


def main() -> int:
    print("Ets Quincaillerie Franck — démarrage du serveur local...")

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
