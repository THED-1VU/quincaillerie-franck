"""Point d'entrée du noyau serveur (cycle 3 — chantiers C2, C3, C11).

Ce serveur ne construit AUCUN écran (pas de HTML, pas de gabarit) et
n'implémente AUCUNE règle métier de vente ou de stock (le décrément de
stock, le calcul de TVA, la composition d'un panier restent hors de ce
cycle). Il pose la colonne vertébrale : authentification, habilitations
appliquées au niveau des requêtes SQL, sécurité applicative de base.

Lancer en développement :
    server\\.venv\\Scripts\\uvicorn.exe app.main:app --reload --app-dir server
"""

from __future__ import annotations

import logging

import psycopg
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from .config import Config, ErreurConfiguration, charger_config
from .database import BaseDeDonnees
from .routes import auth, demonstration
from .securite import GestionnaireSessions, LimiteurDebit

logger = logging.getLogger("quincaillerie")


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
