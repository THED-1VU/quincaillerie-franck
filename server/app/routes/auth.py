"""Authentification (chantier C2) : connexion, changement de mot de passe,
déverrouillage d'un compte par le responsable.

Ces trois routes sont le cœur du chantier C2 — ce ne sont pas les
« deux ou trois routes de démonstration » demandées pour C3 (celles-ci sont
dans routes/demonstration.py) : sans elles, il n'y a rien à authentifier.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from .. import securite
from ..config import Config
from ..database import BaseDeDonnees
from ..deps import exiger_role, obtenir_bd, obtenir_session
from ..roles import role_pg
from ..schemas import (
    DemandeChangementMotDePasse,
    DemandeConnexion,
    ReponseConnexion,
    ReponseDeverrouillage,
)
from ..securite import Session

routeur = APIRouter(prefix="/auth", tags=["authentification"])
routeur_admin = APIRouter(prefix="/admin", tags=["administration"])

# Messages publics : volontairement peu précis pour un identifiant inconnu ou
# un mauvais mot de passe (on ne révèle pas quels identifiants existent),
# mais explicites pour un compte désactivé ou verrouillé — l'utilisateur doit
# savoir qu'il doit voir le responsable, pas continuer à essayer.
_MESSAGES_PUBLICS = {
    "identifiant_ou_mot_de_passe_incorrect": "Identifiant ou mot de passe incorrect.",
    "compte_desactive": "Ce compte est désactivé. Voyez le responsable.",
    "compte_verrouille": (
        "Compte verrouillé après plusieurs échecs. "
        "Voyez le responsable pour le débloquer."
    ),
}


@routeur.post("/connexion", response_model=ReponseConnexion)
def connexion(demande: DemandeConnexion, request: Request):
    limiteur: securite.LimiteurDebit = request.app.state.limiteur_connexion
    cle_limite = demande.identifiant.strip().lower()
    if not limiteur.autorise(cle_limite):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Trop de tentatives de connexion. Réessayez dans une minute.",
        )

    bd: BaseDeDonnees = obtenir_bd(request)
    adresse_ip = request.client.host if request.client else None

    with bd.connexion_anonyme() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM verifier_connexion(%s, %s, %s, %s)",
                (demande.identifiant, demande.mot_de_passe, adresse_ip, "api"),
            )
            ligne = cur.fetchone()
        conn.commit()

    if not ligne["ok"]:
        message = _MESSAGES_PUBLICS.get(ligne["motif"], "Connexion refusée.")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, message)

    # Une connexion réussie efface le compteur de la limitation de débit :
    # ce n'est pas parce qu'on a tâtonné avant de trouver le bon mot de passe
    # qu'on doit rester bridé après coup.
    limiteur.reinitialiser(cle_limite)

    gestionnaire: securite.GestionnaireSessions = request.app.state.gestionnaire_sessions
    jeton = gestionnaire.emettre(
        utilisateur_id=ligne["utilisateur_id"],
        role=ligne["role"],
        site_id=ligne["site_id"],
        nom_complet=ligne["nom_complet"],
        doit_changer_mot_de_passe=ligne["doit_changer_mot_de_passe"],
    )
    config: Config = request.app.state.config
    return ReponseConnexion(
        jeton=jeton,
        expire_dans_secondes=config.api.duree_session_minutes * 60,
        utilisateur_id=ligne["utilisateur_id"],
        nom_complet=ligne["nom_complet"],
        role=ligne["role"],
        site_id=ligne["site_id"],
        doit_changer_mot_de_passe=ligne["doit_changer_mot_de_passe"],
    )


@routeur.post("/changer-mot-de-passe", status_code=status.HTTP_204_NO_CONTENT)
def changer_mot_de_passe(
    demande: DemandeChangementMotDePasse,
    request: Request,
    session: Session = Depends(obtenir_session),
):
    bd: BaseDeDonnees = obtenir_bd(request)
    nouveau_hash = securite.hacher_mot_de_passe(demande.nouveau_mot_de_passe)

    # changer_mon_mot_de_passe vérifie ELLE-MÊME le mot de passe actuel et se
    # limite à qf_utilisateur_courant() : peu importe le rôle, la fonction ne
    # peut de toute façon toucher que la ligne de l'appelant.
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT changer_mon_mot_de_passe(%s, %s) AS ok",
                (demande.mot_de_passe_actuel, nouveau_hash),
            )
            ok = cur.fetchone()["ok"]
        # Pas de commit() manuel ici : connexion_pour() a déjà ouvert une
        # transaction (conn.transaction()) qui commit automatiquement à la
        # sortie normale du bloc `with` ci-dessus — un commit() explicite à
        # l'intérieur est même explicitement refusé par psycopg3.

    if not ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Mot de passe actuel incorrect.")


@routeur_admin.post(
    "/comptes/{utilisateur_id}/deverrouiller",
    response_model=ReponseDeverrouillage,
    dependencies=[],
)
def deverrouiller_compte(
    utilisateur_id: int,
    request: Request,
    session: Session = Depends(exiger_role("responsable")),
):
    """Déverrouille un compte bloqué après trop d'échecs de connexion.

    Réservé au responsable (cahier des charges §3.1 : « Verrouillage du
    compte après plusieurs tentatives échouées, réactivable par le
    responsable »). N'est pas un écran d'administration complet : une seule
    action, celle que l'authentification (C2) exige pour boucler le cycle
    verrouillage -> déverrouillage.
    """
    bd: BaseDeDonnees = obtenir_bd(request)

    with bd.connexion_pour("qf_responsable", utilisateur_id=session.utilisateur_id) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT tentatives_echouees FROM utilisateurs WHERE id = %s",
                (utilisateur_id,),
            )
            ligne = cur.fetchone()
            if ligne is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Compte introuvable.")

            ancienne_valeur = ligne["tentatives_echouees"]
            cur.execute(
                "UPDATE utilisateurs SET tentatives_echouees = 0 WHERE id = %s",
                (utilisateur_id,),
            )
            cur.execute(
                """
                INSERT INTO journal_comptes
                    (utilisateur_cible_id, action, ancienne_valeur, nouvelle_valeur, utilisateur_auteur_id)
                VALUES (%s, 'deverrouillage', %s, '0', %s)
                """,
                (utilisateur_id, str(ancienne_valeur), session.utilisateur_id),
            )
        # Idem : le commit est automatique à la sortie de connexion_pour().

    return ReponseDeverrouillage(utilisateur_id=utilisateur_id, tentatives_echouees=0)
