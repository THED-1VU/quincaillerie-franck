"""Ressources humaines (chantier C6, cycle 16) — réservé au responsable,
comme le dit le cahier des charges (§3.5) : un agent comptabilité peut
seulement LIRE un employé par son nom pour y rattacher une dépense
(``routes/transactions.py``), jamais gérer les fiches, absences ou
avances lui-même.

Hors périmètre, volontairement : clôture de caisse (addendum, point g,
non tranché) — sans rapport avec la RH, mais rappelé ici pour mémoire, ce
module ne traite que ``employes``, ``absences_conges`` et
``avances_salaire``.
"""

from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..deps import exiger_role, obtenir_bd
from ..erreurs import erreur_metier
from ..roles import role_pg
from ..schemas import (
    DemandeAbsenceConge,
    DemandeAvanceSalaire,
    DemandeEmploye,
    ReponseAbsenceConge,
    ReponseAvanceSalaire,
    ReponseEmploye,
)
from ..securite import Session

routeur = APIRouter(prefix="/rh", tags=["ressources humaines"])


@routeur.post("/employes", response_model=ReponseEmploye, status_code=status.HTTP_201_CREATED)
def creer_employe(
    demande: DemandeEmploye,
    request: Request,
    session: Session = Depends(exiger_role("responsable")),
):
    bd = obtenir_bd(request)
    with bd.connexion_pour(role_pg(session.role), utilisateur_id=session.utilisateur_id) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO employes (nom_complet, poste, telephone, type_contrat, salaire_mensuel, site_id, date_embauche)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, actif
                    """,
                    (
                        demande.nom_complet, demande.poste, demande.telephone, demande.type_contrat,
                        demande.salaire_mensuel, demande.site_id, demande.date_embauche,
                    ),
                )
            except psycopg.errors.ForeignKeyViolation as exc:
                raise erreur_metier(exc) from exc
            ligne = cur.fetchone()

    return ReponseEmploye(
        employe_id=ligne["id"], nom_complet=demande.nom_complet, poste=demande.poste,
        telephone=demande.telephone, type_contrat=demande.type_contrat,
        salaire_mensuel=demande.salaire_mensuel, site_id=demande.site_id, actif=ligne["actif"],
    )


@routeur.get("/employes")
def lister_employes(
    request: Request,
    session: Session = Depends(exiger_role("responsable")),
):
    bd = obtenir_bd(request)
    with bd.connexion_pour(role_pg(session.role), utilisateur_id=session.utilisateur_id) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id AS employe_id, nom_complet, poste, telephone, type_contrat,
                       salaire_mensuel, site_id, actif
                  FROM employes
                 ORDER BY nom_complet
                """
            )
            lignes = cur.fetchall()

    return {"employes": lignes}


@routeur.post("/absences-conges", response_model=ReponseAbsenceConge, status_code=status.HTTP_201_CREATED)
def creer_absence_conge(
    demande: DemandeAbsenceConge,
    request: Request,
    session: Session = Depends(exiger_role("responsable")),
):
    bd = obtenir_bd(request)
    with bd.connexion_pour(role_pg(session.role), utilisateur_id=session.utilisateur_id) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO absences_conges (employe_id, type, date_debut, date_fin, motif, utilisateur_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        demande.employe_id, demande.type, demande.date_debut,
                        demande.date_fin, demande.motif, session.utilisateur_id,
                    ),
                )
            except (psycopg.errors.ForeignKeyViolation, psycopg.errors.CheckViolation) as exc:
                raise erreur_metier(exc) from exc
            id_cree = cur.fetchone()["id"]

    return ReponseAbsenceConge(
        id=id_cree, employe_id=demande.employe_id, type=demande.type,
        date_debut=demande.date_debut, date_fin=demande.date_fin, motif=demande.motif,
    )


@routeur.get("/absences-conges")
def lister_absences_conges(
    request: Request,
    session: Session = Depends(exiger_role("responsable")),
):
    bd = obtenir_bd(request)
    with bd.connexion_pour(role_pg(session.role), utilisateur_id=session.utilisateur_id) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT a.id, a.employe_id, e.nom_complet AS employe_nom, a.type,
                       a.date_debut, a.date_fin, a.motif
                  FROM absences_conges a
                  JOIN employes e ON e.id = a.employe_id
                 ORDER BY a.date_debut DESC
                """
            )
            lignes = cur.fetchall()

    return {"absences_conges": lignes}


@routeur.post("/avances-salaire", response_model=ReponseAvanceSalaire, status_code=status.HTTP_201_CREATED)
def creer_avance_salaire(
    demande: DemandeAvanceSalaire,
    request: Request,
    session: Session = Depends(exiger_role("responsable")),
):
    bd = obtenir_bd(request)
    with bd.connexion_pour(role_pg(session.role), utilisateur_id=session.utilisateur_id) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO avances_salaire (employe_id, montant, motif, utilisateur_id)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, remboursee
                    """,
                    (demande.employe_id, demande.montant, demande.motif, session.utilisateur_id),
                )
            except psycopg.errors.ForeignKeyViolation as exc:
                raise erreur_metier(exc) from exc
            ligne = cur.fetchone()

    return ReponseAvanceSalaire(
        id=ligne["id"], employe_id=demande.employe_id, montant=demande.montant,
        motif=demande.motif, remboursee=ligne["remboursee"],
    )


@routeur.get("/avances-salaire")
def lister_avances_salaire(
    request: Request,
    session: Session = Depends(exiger_role("responsable")),
):
    bd = obtenir_bd(request)
    with bd.connexion_pour(role_pg(session.role), utilisateur_id=session.utilisateur_id) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT v.id, v.employe_id, e.nom_complet AS employe_nom, v.montant,
                       v.motif, v.remboursee, v.date_avance
                  FROM avances_salaire v
                  JOIN employes e ON e.id = v.employe_id
                 ORDER BY v.date_avance DESC
                """
            )
            lignes = cur.fetchall()

    return {"avances_salaire": lignes}


@routeur.post("/avances-salaire/{avance_id}/rembourser", status_code=status.HTTP_204_NO_CONTENT)
def rembourser_avance_salaire(
    avance_id: int,
    request: Request,
    session: Session = Depends(exiger_role("responsable")),
):
    """Marque une avance comme remboursée — jamais l'inverse : une fois
    remboursée, ça ne se « dé-rembourse » pas (pas de route pour ça,
    comme une vente encaissée ne se ré-ouvre pas)."""
    bd = obtenir_bd(request)
    with bd.connexion_pour(role_pg(session.role), utilisateur_id=session.utilisateur_id) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE avances_salaire SET remboursee = TRUE WHERE id = %s AND remboursee = FALSE RETURNING id",
                (avance_id,),
            )
            ligne = cur.fetchone()
    if ligne is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Avance introuvable, ou déjà remboursée.",
        )
