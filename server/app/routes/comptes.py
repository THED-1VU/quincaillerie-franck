"""Gestion des comptes depuis l'application (chantier C2, cycle 32).

Réservé au responsable, conformément au cahier des charges §3.8 (GS §3,
DR Resp. B1-B3) et à la décision du 2026-09-20 : création de comptes PAR
LE RESPONSABLE depuis l'intérieur de l'app, jamais d'auto-inscription
publique.

Règles tranchées par le propriétaire le 2026-09-20 :
- le responsable crée des AGENTS uniquement (``agent_stock`` ou
  ``agent_comptabilite``, site obligatoire) — le premier compte responsable
  relève de l'outil C0-C (``db/outils/creer_compte_responsable.ps1``),
  jamais de ces routes ;
- un responsable ne peut pas désactiver son propre compte ;
- le dernier responsable actif ne peut pas être désactivé ;
- un compte désactivé est coupé immédiatement : la requête suivante est
  refusée (voir ``deps.obtenir_session`` et la migration 024) ;
- réinitialisation du mot de passe d'un agent par le responsable
  (cycle 38, décision 2026-09-22) : le responsable saisit le nouveau mot
  de passe (>= 8 caractères), jamais restitué, changement forcé à la
  première connexion (``reinitialiser_mot_de_passe_agent()``, migration 033).

Le hachage du mot de passe n'est jamais lu ni restitué : l'INSERT écrit un
hachage produit ici (``securite.hacher_mot_de_passe``), et les SELECT ne
portent que sur les colonnes autorisées au rôle responsable (migration 008).
"""

from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request, status

from .. import securite
from ..deps import exiger_role, obtenir_bd
from ..erreurs import erreur_metier
from ..roles import role_pg
from ..schemas import (
    DemandeActifCompte,
    DemandeCompte,
    DemandeReinitialisationMotDePasse,
    ReponseCompte,
    ReponseReinitialisationMotDePasse,
)
from ..securite import Session

routeur = APIRouter(prefix="/admin/comptes", tags=["administration"])

_COLONNES_PROFIL = (
    "id, nom_complet, identifiant, role, site_id, actif, "
    "doit_changer_mot_de_passe, date_creation"
)


def _profil(cur, compte_id: int):
    cur.execute(
        f"SELECT {_COLONNES_PROFIL} FROM utilisateurs WHERE id = %s",
        (compte_id,),
    )
    ligne = cur.fetchone()
    if ligne is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compte introuvable.")
    return ligne


@routeur.get("")
def lister_comptes(
    request: Request,
    session: Session = Depends(exiger_role("responsable")),
):
    bd = obtenir_bd(request)
    with bd.connexion_pour(role_pg(session.role), utilisateur_id=session.utilisateur_id) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_COLONNES_PROFIL} FROM utilisateurs "
                "ORDER BY role, identifiant"
            )
            lignes = cur.fetchall()
    return {"comptes": lignes}


@routeur.post("", response_model=ReponseCompte, status_code=status.HTTP_201_CREATED)
def creer_compte(
    demande: DemandeCompte,
    request: Request,
    session: Session = Depends(exiger_role("responsable")),
):
    identifiant = demande.identifiant.strip()
    if not identifiant:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "L'identifiant est obligatoire.")

    hash_mdp = securite.hacher_mot_de_passe(demande.mot_de_passe)

    bd = obtenir_bd(request)
    with bd.connexion_pour(role_pg(session.role), utilisateur_id=session.utilisateur_id) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM utilisateurs WHERE identifiant = %s",
                (identifiant,),
            )
            if cur.fetchone() is not None:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "Cet identifiant est déjà utilisé.",
                )

            try:
                cur.execute(
                    """
                    INSERT INTO utilisateurs (nom_complet, identifiant, mot_de_passe_hash,
                                              role, site_id, actif, doit_changer_mot_de_passe)
                    VALUES (%s, %s, %s, %s, %s, TRUE, TRUE)
                    RETURNING id
                    """,
                    (
                        demande.nom_complet.strip(), identifiant, hash_mdp,
                        demande.role, demande.site_id,
                    ),
                )
                compte_id = cur.fetchone()["id"]
            except psycopg.errors.ForeignKeyViolation as exc:
                raise erreur_metier(exc) from exc
            except psycopg.errors.UniqueViolation:
                # Course entre le pré-contrôle et l'INSERT : même réponse
                # claire que si le doublon avait été vu avant.
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "Cet identifiant est déjà utilisé.",
                )

            cur.execute(
                """
                INSERT INTO journal_comptes
                    (utilisateur_cible_id, action, utilisateur_auteur_id)
                VALUES (%s, 'creation', %s)
                """,
                (compte_id, session.utilisateur_id),
            )
            profil = _profil(cur, compte_id)

    return ReponseCompte(**profil)


@routeur.patch("/{compte_id}/actif", response_model=ReponseCompte)
def changer_actif_compte(
    compte_id: int,
    demande: DemandeActifCompte,
    request: Request,
    session: Session = Depends(exiger_role("responsable")),
):
    bd = obtenir_bd(request)
    with bd.connexion_pour(role_pg(session.role), utilisateur_id=session.utilisateur_id) as conn:
        with conn.cursor() as cur:
            profil = _profil(cur, compte_id)

            if not demande.actif and compte_id == session.utilisateur_id:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "Vous ne pouvez pas désactiver votre propre compte.",
                )

            if not demande.actif and profil["role"] == "responsable":
                cur.execute(
                    "SELECT count(*) AS nb FROM utilisateurs "
                    "WHERE role = 'responsable' AND actif = TRUE"
                )
                if cur.fetchone()["nb"] <= 1:
                    raise HTTPException(
                        status.HTTP_422_UNPROCESSABLE_ENTITY,
                        "Impossible de désactiver le dernier responsable actif.",
                    )

            cur.execute(
                "UPDATE utilisateurs SET actif = %s WHERE id = %s",
                (demande.actif, compte_id),
            )
            cur.execute(
                """
                INSERT INTO journal_comptes
                    (utilisateur_cible_id, action, ancienne_valeur, nouvelle_valeur,
                     utilisateur_auteur_id)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    compte_id,
                    "desactivation" if not demande.actif else "reactivation",
                    str(profil["actif"]).lower(),
                    str(demande.actif).lower(),
                    session.utilisateur_id,
                ),
            )
            profil = _profil(cur, compte_id)

    return ReponseCompte(**profil)


@routeur.patch(
    "/{compte_id}/mot-de-passe",
    response_model=ReponseReinitialisationMotDePasse,
)
def reinitialiser_mot_de_passe(
    compte_id: int,
    demande: DemandeReinitialisationMotDePasse,
    request: Request,
    session: Session = Depends(exiger_role("responsable")),
):
    """Réinitialisation du mot de passe d'un AGENT par le responsable
    (cycle 38, décision 2026-09-22) : le responsable saisit le nouveau mot
    de passe (>= 8 caractères), il n'est JAMAIS restitué, et l'agent devra
    le changer à sa première connexion. La vraie protection est en base :
    ``reinitialiser_mot_de_passe_agent()`` (migration 033, SECURITY DEFINER,
    réservée à qf_responsable) refuse un mot de passe court et refuse de
    viser un compte responsable."""
    bd = obtenir_bd(request)
    with bd.connexion_pour(role_pg(session.role), utilisateur_id=session.utilisateur_id) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "SELECT reinitialiser_mot_de_passe_agent(%s, %s, %s)",
                    (compte_id, demande.mot_de_passe, session.utilisateur_id),
                )
            except (
                psycopg.errors.ForeignKeyViolation,
                psycopg.errors.CheckViolation,
            ) as exc:
                raise erreur_metier(exc) from exc

            cur.execute(
                "SELECT doit_changer_mot_de_passe FROM utilisateurs WHERE id = %s",
                (compte_id,),
            )
            ligne = cur.fetchone()
            if ligne is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Compte introuvable.")

    return ReponseReinitialisationMotDePasse(
        compte_id=compte_id,
        doit_changer_mot_de_passe=ligne["doit_changer_mot_de_passe"],
    )
