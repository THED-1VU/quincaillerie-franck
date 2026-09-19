"""Point d'entrée du noyau serveur.

Cycle 3 (chantiers C2, C3, C11) a posé l'authentification, les habilitations
au niveau des requêtes SQL et la sécurité applicative de base — sans écran,
sans règle métier de vente ou de stock.

Cycle 5 (chantiers C9/C10) y a ajouté le service des fichiers statiques de
la maquette (`maquette/`, cycle 1) sous `/app` : même origine que l'API,
donc aucun CORS à gérer, conforme à l'architecture actée (« un seul code
applicatif web »).

Cycle 6 (chantier C5) y a ajouté la première route métier de vente
(`routes/ventes.py`) — voir ce module pour les décisions du propriétaire
qu'elle applique (addendum, points b/d/e) et celle qu'elle laisse
volontairement de côté (point c, non tranché).

Cycle 7 (chantier C7) y a ajouté le comptage d'inventaire à l'aveugle et
les écarts (`routes/inventaire.py`) — voir ce module pour la garantie
qu'aucune quantité attendue n'atteint jamais le navigateur de l'agent
stock.

Cycle 9 (chantier C4) y ajoute la création d'articles (`routes/
articles.py`) et les mouvements de stock — réception, transfert
inter-sites, casse, retours client/fournisseur (`routes/stock.py`) — voir
`db/migrations/014_...` pour les décisions du propriétaire qu'ils
appliquent (addendum, points a et f).

Cycle 10 (chantier C8) y ajoute la dernière carte du tableau de bord
encore simulée (`routes/tableau_bord.py`, alertes de stock faible), un
historique des comptages filtrable par période (`routes/inventaire.py`),
et deux exports de rapports (`routes/rapports.py`, Excel/PDF) dont le
gating du prix par rôle est posé dans la clause SQL elle-même (voir
`app/colonnes.py`) — jamais retiré du fichier après coup.

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
from .roles import role_pg
from .routes import (
    articles,
    auth,
    caisse,
    configuration,
    demonstration,
    exploitation,
    inventaire,
    rapports,
    rh,
    stock,
    tableau_bord,
    transactions,
    ventes,
)
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
        title="Akuma — noyau serveur",
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

    # Cycle 28 : lu UNE FOIS au démarrage, jamais au moment de l'erreur —
    # c'est justement quand la base est INJOIGNABLE que ce message doit
    # s'afficher (voir le gestionnaire d'exception plus bas) ; la relire à
    # cet instant précis échouerait ou attendrait elle-même. Redémarrer le
    # serveur est nécessaire pour qu'un changement de ce paramètre soit pris
    # en compte — acceptable pour une valeur qui ne change presque jamais.
    app.state.contact_support = None
    try:
        with app.state.bd.connexion_pour(role_pg("responsable")) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT valeur FROM parametres WHERE cle = 'contact_support_technique'")
                ligne = cur.fetchone()
                if ligne and ligne["valeur"] and ligne["valeur"] != "a_definir":
                    app.state.contact_support = ligne["valeur"]
    except psycopg.Error:
        logger.warning("Impossible de lire contact_support_technique au démarrage — omis du message d'indisponibilité.")

    # -----------------------------------------------------------------
    # En-têtes HTTP de sécurité (chantier C11, cycle 21) : posés sur TOUTE
    # réponse, API comme écrans statiques sous /app — protection technique
    # au niveau du navigateur, indépendante des habilitations posées en base
    # (privilèges par colonne + RLS, cycle 2), qui restent le contrôle qui
    # compte vraiment (voir deps.py).
    # -----------------------------------------------------------------
    @app.middleware("http")
    async def _en_tetes_securite(request: Request, appel_suivant):
        reponse = await appel_suivant(request)
        # Un navigateur ne doit jamais deviner le type MIME d'une réponse à
        # la place du Content-Type déclaré (empêche un fichier détourné en
        # script exécutable).
        reponse.headers["X-Content-Type-Options"] = "nosniff"
        # Aucun écran de ce projet n'a besoin d'être intégré dans une
        # <iframe> d'un autre site (architecture "un seul code applicatif
        # web", même origine) : DENY plutôt que SAMEORIGIN, le plus strict.
        reponse.headers["X-Frame-Options"] = "DENY"
        # Ne jamais transmettre l'URL complète (avec un futur jeton en
        # requête, un identifiant de vente...) au site externe référencé par
        # un lien sortant.
        reponse.headers["Referrer-Policy"] = "no-referrer"
        return reponse

    app.include_router(auth.routeur)
    app.include_router(auth.routeur_admin)
    app.include_router(demonstration.routeur)
    app.include_router(ventes.routeur)
    app.include_router(inventaire.routeur)
    app.include_router(articles.routeur)
    app.include_router(stock.routeur)
    app.include_router(tableau_bord.routeur)
    app.include_router(rapports.routeur)
    app.include_router(transactions.routeur)
    app.include_router(rh.routeur)
    app.include_router(caisse.routeur)
    app.include_router(exploitation.routeur)
    app.include_router(configuration.routeur)

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

    # -----------------------------------------------------------------
    # Base de données injoignable (chantier C12, cycle 28) — DISTINCT du
    # gestionnaire générique ci-dessous : « la base a refusé la requête »
    # (bug applicatif, contrainte violée) n'est PAS la même situation que
    # « la base ne répond pas du tout » (panne, redémarrage en cours).
    # Exigé par le propriétaire (2026-09-18), en français simple, SANS
    # jargon ni code d'erreur visible : que la base ne répond pas, que ce
    # n'est pas la faute du vendeur, que ce qu'il a déjà saisi à l'écran
    # n'est pas perdu, et qui prévenir. Le détail technique (exception,
    # traceback) va SEULEMENT au journal serveur — jamais sur l'écran du
    # comptoir. Trouvé par exécution (PostgreSQL arrêté délibérément) :
    # sans OperationalError distinguée du reste, ce cas tombait dans le
    # message générique "Erreur interne.", qui ne dit rien de tout cela.
    # -----------------------------------------------------------------
    @app.exception_handler(psycopg.OperationalError)
    def _base_injoignable(request: Request, exc: psycopg.OperationalError):
        logger.error("Base de données injoignable sur %s", request.url.path, exc_info=exc)
        # Message VOLONTAIREMENT generique : ce gestionnaire s'applique a
        # TOUTE route (vente, connexion, RH, rapports...), pas seulement
        # l'ecran de caisse — "les articles saisis" n'aurait pas de sens
        # pour un echec de connexion, par exemple.
        message = (
            "L'application n'arrive pas à joindre son système d'enregistrement en ce moment. "
            "Ce n'est pas un problème de votre côté. Ce que vous avez déjà saisi à l'écran "
            "n'est pas perdu — ne rechargez pas la page : vous pourrez continuer dès que "
            "la connexion sera rétablie."
        )
        if request.app.state.contact_support:
            message += f" En attendant, prévenez : {request.app.state.contact_support}."
        return JSONResponse(
            {"detail": message}, status_code=status.HTTP_503_SERVICE_UNAVAILABLE
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
