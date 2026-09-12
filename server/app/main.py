"""Point d'entrée du noyau serveur.

Cycle 3 (chantiers C2, C3, C11) a posé l'authentification, les habilitations
au niveau des requêtes SQL et la sécurité applicative de base — sans écran,
sans règle métier de vente ou de stock.

Cycle 5 (chantiers C9/C10) y a ajouté le service des fichiers statiques de
la maquette (`maquette/`, cycle 1) sous `/app` : même origine que l'API,
donc aucun CORS à gérer, conforme à l'architecture actée (« un seul code
applicatif web »).

Cycle 6 (chantier C5) y ajoute la première route métier de vente
(`routes/ventes.py`) — voir ce module pour les décisions du propriétaire
qu'elle applique (addendum, points b/d/e) et celle qu'elle laisse
volontairement de côté (point c, non tranché).

Lancer en développement :
    server\\.venv\\Scripts\\uvicorn.exe app.main:app --reload --app-dir server
"""

from __future__ import annotations

import logging
from pathlib import Path

import psycopg
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import Config, ErreurConfiguration, charger_config
from .database import BaseDeDonnees
from .routes import auth, demonstration, ventes
from .securite import GestionnaireSessions, LimiteurDebit

logger = logging.getLogger("quincaillerie")

# maquette/ est à la racine du dépôt, deux niveaux au-dessus de server/app/.
# NOTE (portée du cycle 5, C9/C10 uniquement — ne touche pas C0) : ce chemin
# fonctionne en développement (uvicorn lancé depuis le dépôt). L'empaquetage
# de ces fichiers DANS l'exécutable (server/fabrication/, chantier C0) n'a
# pas été fait ce cycle — voir RAPPORT AVANCEMENT/loop-state.md, « reste à
# faire ». Le montage est donc toléré manquant (avertissement, pas un crash)
# pour ne pas casser l'exécutable déjà construit au cycle 4.
RACINE_DEPOT = Path(__file__).resolve().parent.parent.parent
MAQUETTE_DIR = RACINE_DEPOT / "maquette"


def creer_application(config: Config | None = None) -> FastAPI:
    if config is None:
        config = charger_config()

    app = FastAPI(
        title="Quincaillerie Franck — noyau serveur",
        description=(
            "Authentification et habilitations. Aucun écran, aucune règle "
            "métier de vente/stock : voir README.md."
        ),
        version="cycle-3",
    )

    app.state.config = config
    app.state.bd = BaseDeDonnees(config)
    app.state.gestionnaire_sessions = GestionnaireSessions(
        config.api.secret_key, config.api.duree_session_minutes
    )
    app.state.limiteur_connexion = LimiteurDebit(config.api.tentatives_max_par_minute)

    app.include_router(auth.routeur)
    app.include_router(auth.routeur_admin)
    app.include_router(demonstration.routeur)
    app.include_router(ventes.routeur)

    if MAQUETTE_DIR.is_dir():
        app.mount("/app", StaticFiles(directory=str(MAQUETTE_DIR), html=True), name="maquette")
    else:
        logger.warning(
            "Dossier maquette introuvable (%s) : les écrans ne seront pas servis, "
            "seule l'API répond.", MAQUETTE_DIR,
        )

    @app.get("/sante", tags=["exploitation"])
    def sante():
        """Vérifie que le serveur répond et que la base est joignable — sans
        authentification, réservé au monitoring, ne renvoie aucune donnée."""
        try:
            with app.state.bd.connexion_anonyme() as conn:
                conn.execute("SELECT 1")
        except psycopg.Error:
            logger.exception("Base de données injoignable")
            return JSONResponse(
                {"etat": "degrade", "base": "injoignable"},
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return {"etat": "ok", "base": "joignable"}

    # -----------------------------------------------------------------
    # Sécurité (C11) : ne jamais renvoyer le détail d'une erreur SQL au
    # client — ni le nom d'une table ou d'une colonne, ni le texte d'une
    # contrainte. Le contrôle réel (habilitations, RLS) a déjà eu lieu côté
    # PostgreSQL ; ici on se contente de traduire en code HTTP compréhensible
    # et de journaliser le détail côté serveur, pas côté client.
    # -----------------------------------------------------------------
    @app.exception_handler(psycopg.errors.InsufficientPrivilege)
    def _acces_refuse_par_la_base(request: Request, exc: psycopg.errors.InsufficientPrivilege):
        logger.warning("Accès refusé par PostgreSQL sur %s : %s", request.url.path, exc)
        return JSONResponse(
            {"detail": "Accès refusé."}, status_code=status.HTTP_403_FORBIDDEN
        )

    @app.exception_handler(psycopg.Error)
    def _erreur_base_generique(request: Request, exc: psycopg.Error):
        # logger.exception() suppose une exception "en cours" (sys.exc_info()) ;
        # ici on est dans un gestionnaire Starlette appelé APRÈS coup, avec
        # l'exception passée en argument — il faut donc exc_info=exc explicite,
        # sinon le journal affiche "NoneType: None" au lieu de la vraie erreur.
        logger.error("Erreur base de données sur %s", request.url.path, exc_info=exc)
        return JSONResponse(
            {"detail": "Erreur interne."}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return app


try:
    app = creer_application()
except ErreurConfiguration as exc:  # pragma: no cover - message d'aide au démarrage
    raise SystemExit(f"Configuration invalide : {exc}") from exc
