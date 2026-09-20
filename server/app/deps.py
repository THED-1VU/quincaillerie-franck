"""Dépendances FastAPI : extraction et vérification de la session, contrôle
du rôle demandé par une route.

Point de contrôle applicatif des habilitations (chantier C3) — mais ce n'est
qu'une première haie, pas la clôture : le contrôle qui compte vraiment reste
celui de PostgreSQL (privilèges par colonne + RLS posés au cycle 2), qui
s'applique quel que soit l'état de ce code. Un bug ici ferait au pire
répondre 403 à tort ou refuser une route légitime — jamais fuiter une donnée
interdite, parce que la requête SQL sous-jacente resterait bloquée par la
base.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from .database import BaseDeDonnees
from .securite import GestionnaireSessions, JetonInvalide, Session


def obtenir_bd(request: Request) -> BaseDeDonnees:
    return request.app.state.bd


def obtenir_gestionnaire_sessions(request: Request) -> GestionnaireSessions:
    return request.app.state.gestionnaire_sessions


def obtenir_session(
    request: Request,
    gestionnaire: GestionnaireSessions = Depends(obtenir_gestionnaire_sessions),
) -> Session:
    entete = request.headers.get("authorization", "")
    if not entete.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Jeton manquant.")
    jeton = entete[len("bearer "):].strip()
    if not jeton:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Jeton manquant.")
    try:
        session = gestionnaire.verifier(jeton)
    except JetonInvalide as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

    # Révocation (chantier C11, cycle 21) et compte désactivé (chantier C2,
    # cycle 32) : la signature et l'expiration ne suffisent plus — un jeton
    # peut être signature-valide et pourtant explicitement révoqué, et un
    # compte peut être désactivé par le responsable alors qu'une session est
    # en cours (décision du 2026-09-20 : la requête suivante est refusée).
    # Vérifié SOUS qf_app (connexion_anonyme, comme verifier_connexion),
    # avant toute bascule de rôle : ces deux faits ne sont pas des données
    # métier cloisonnées par site. Un jeton antérieur au cycle 21 a jti=\"\"
    # (securite.py) — jeton_est_revoque(\"\") ne trouve jamais de ligne,
    # comportement inchangé pour lui (jamais révocable, comme avant ce
    # cycle) ; le contrôle d'activité, lui, s'applique à tous les jetons.
    bd: BaseDeDonnees = obtenir_bd(request)
    with bd.connexion_anonyme() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT jeton_est_revoque(%s) AS revoque, "
                "       compte_est_actif(%s) AS actif",
                (session.jti, session.utilisateur_id),
            )
            ligne = cur.fetchone()
            if ligne["revoque"]:
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session déconnectée, reconnectez-vous.")
            if not ligne["actif"]:
                raise HTTPException(
                    status.HTTP_401_UNAUTHORIZED,
                    "Ce compte est désactivé. Voyez le responsable.",
                )

    return session


def exiger_role(*roles_autorises: str):
    """Fabrique une dépendance qui n'accepte que les rôles listés.

    Un seul point de définition par route protégée — jamais de
    ``if session.role == ...`` recopié dans chaque fonction de route.
    """

    def dependance(session: Session = Depends(obtenir_session)) -> Session:
        if session.role not in roles_autorises:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "Rôle non autorisé pour cette route."
            )
        return session

    return dependance
