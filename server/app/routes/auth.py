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

    bd: BaseDeDonnees = obtenir_bd(request)
    adresse_ip = request.client.host if request.client else None
    config: Config = request.app.state.config

    with bd.connexion_anonyme() as conn:
        with conn.cursor() as cur:
            # Limiteur de débit PARTAGÉ entre processus (chantier C11,
            # cycle 44) : le compteur vit en base (migration 038), pas en
            # mémoire. Repli volontaire sur le limiteur en mémoire si la
            # base ne répond pas — la limitation ne doit jamais bloquer la
            # connexion elle-même.
            autorise = True
            try:
                cur.execute(
                    "SELECT tentative_autorisee(%s, %s, %s) AS autorise",
                    (cle_limite, limiteur.max_essais, limiteur.fenetre_secondes),
                )
                autorise = bool(cur.fetchone()["autorise"])
            except Exception:  # noqa: BLE001 - repli en mémoire, jamais bloquant
                autorise = limiteur.autorise(cle_limite)
            if not autorise:
                raise HTTPException(
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    "Trop de tentatives de connexion. Réessayez dans une minute.",
                )

            cur.execute(
                "SELECT * FROM verifier_connexion(%s, %s, %s, %s)",
                (demande.identifiant, demande.mot_de_passe, adresse_ip, "api"),
            )
            ligne = cur.fetchone()
            # Durée de session : valeur DÉCIDÉE en base (parametres, migration
            # 033) — le config.ini ne sert que de repli si la base ne répond
            # pas. Une seule source de vérité, la base sauvegardée.
            duree_minutes = config.api.duree_session_minutes
            roles = [ligne["role"]]
            if ligne["ok"]:
                try:
                    cur.execute("SELECT duree_session_minutes_decidee() AS minutes")
                    valeur = cur.fetchone()["minutes"]
                    if valeur is not None:
                        duree_minutes = int(valeur)
                except Exception:  # noqa: BLE001 - repli volontaire, jamais bloquant
                    duree_minutes = config.api.duree_session_minutes
                # Cumul de rôles (chantier C3, cycle 41) : la liste complète
                # des rôles effectifs accompagne le rôle principal dans le
                # jeton. Si la table n'existe pas encore (migration 035 non
                # appliquée), le rôle principal seul est conservé.
                try:
                    cur.execute(
                        "SELECT role FROM roles_utilisateur(%s)",
                        (ligne["utilisateur_id"],),
                    )
                    roles = [r["role"] for r in cur.fetchall()] or [ligne["role"]]
                except Exception:  # noqa: BLE001 - repli volontaire
                    roles = [ligne["role"]]
                # Une connexion réussie efface le compteur du limiteur : ce
                # n'est pas parce qu'on a tâtonné avant de trouver le bon mot
                # de passe qu'on doit rester bridé après coup.
                try:
                    cur.execute(
                        "SELECT reinitialiser_limitation(%s)", (cle_limite,)
                    )
                except Exception:  # noqa: BLE001 - repli en mémoire
                    limiteur.reinitialiser(cle_limite)
        conn.commit()

    if not ligne["ok"]:
        message = _MESSAGES_PUBLICS.get(ligne["motif"], "Connexion refusée.")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, message)

    gestionnaire: securite.GestionnaireSessions = request.app.state.gestionnaire_sessions
    jeton = gestionnaire.emettre(
        utilisateur_id=ligne["utilisateur_id"],
        role=ligne["role"],
        site_id=ligne["site_id"],
        nom_complet=ligne["nom_complet"],
        doit_changer_mot_de_passe=ligne["doit_changer_mot_de_passe"],
        duree_minutes=duree_minutes,
        roles=roles,
    )
    return ReponseConnexion(
        jeton=jeton,
        expire_dans_secondes=duree_minutes * 60,
        utilisateur_id=ligne["utilisateur_id"],
        nom_complet=ligne["nom_complet"],
        role=ligne["role"],
        site_id=ligne["site_id"],
        doit_changer_mot_de_passe=ligne["doit_changer_mot_de_passe"],
    )


@routeur.post("/deconnexion", status_code=status.HTTP_204_NO_CONTENT)
def deconnexion(request: Request, session: Session = Depends(obtenir_session)):
    """Révoque le jeton courant (chantier C11, cycle 21) — jusqu'ici, un
    jeton signé restait valide jusqu'à sa propre expiration, sans moyen de
    forcer une déconnexion. Un jeton émis avant ce cycle n'a pas de ``jti``
    (``session.jti == ""``) : rien à révoquer, la route répond quand même
    204 plutôt que de renvoyer une erreur pour un cas qui n'est pas une
    faute de l'appelant."""
    if not session.jti:
        return
    bd: BaseDeDonnees = obtenir_bd(request)
    with bd.connexion_anonyme() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT revoquer_jeton(%s, %s, %s)",
                (session.jti, session.utilisateur_id, session.expire_a),
            )
        conn.commit()


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
