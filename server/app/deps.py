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
        return gestionnaire.verifier(jeton)
    except JetonInvalide as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc


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
