"""Crédit client (addendum, point b, décidé le 2026-09-25).

Clients partagés entre les deux sites (``site_id`` informatif seulement,
jamais un filtre RLS — un même client peut acheter à crédit au Magasin ou au
Comptoir). Création et modification réservées au responsable (même esprit
que ``rh.py``) ; l'agent comptabilité peut seulement LISTER les clients
(nécessaire pour choisir un client au moment d'une vente à crédit,
``POST /ventes``) et enregistrer un règlement — jamais créer ou modifier une
fiche.

Toute écriture qui touche ``creances``/``reglements_creances`` passe par une
fonction ``SECURITY DEFINER`` (migration 045) : cette route ne fait jamais
de calcul de solde elle-même, ``encours_client()`` fait foi.
"""

from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..deps import exiger_role, obtenir_bd
from ..erreurs import erreur_metier
from ..roles import role_pg
from ..schemas import (
    DemandeActifCompte,
    DemandeClient,
    DemandeReglementCreance,
    ReponseClient,
    ReponseReglementCreance,
)
from ..securite import Session

routeur = APIRouter(prefix="/clients", tags=["clients"])


def _client(cur, client_id: int) -> dict:
    cur.execute(
        """
        SELECT id, nom, telephone, plafond_credit, site_id, actif,
               encours_client(id) AS encours
          FROM clients WHERE id = %s
        """,
        (client_id,),
    )
    ligne = cur.fetchone()
    if ligne is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Client introuvable.")
    return ligne


@routeur.get("", response_model=list[ReponseClient])
def lister_clients(
    request: Request,
    actifs_seulement: bool = True,
    session: Session = Depends(exiger_role("responsable", "agent_comptabilite")),
):
    """Tous les clients, quel que soit le site (partagés) — filtrés sur
    ``actif`` par défaut, pour ne pas polluer le sélecteur de l'écran de
    vente avec des fiches désactivées."""
    bd = obtenir_bd(request)
    with bd.connexion_pour(role_pg(session.role), utilisateur_id=session.utilisateur_id) as conn:
        with conn.cursor() as cur:
            requete = (
                "SELECT id, nom, telephone, plafond_credit, site_id, actif, "
                "encours_client(id) AS encours FROM clients"
            )
            if actifs_seulement:
                requete += " WHERE actif = TRUE"
            requete += " ORDER BY nom"
            cur.execute(requete)
            lignes = cur.fetchall()
    return lignes


@routeur.post("", response_model=ReponseClient, status_code=status.HTTP_201_CREATED)
def creer_client(
    demande: DemandeClient,
    request: Request,
    session: Session = Depends(exiger_role("responsable")),
):
    bd = obtenir_bd(request)
    with bd.connexion_pour(role_pg(session.role), utilisateur_id=session.utilisateur_id) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO clients (nom, telephone, plafond_credit, site_id)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (demande.nom, demande.telephone, demande.plafond_credit, demande.site_id),
            )
            client_id = cur.fetchone()["id"]
            ligne = _client(cur, client_id)
    return ligne


@routeur.put("/{client_id}", response_model=ReponseClient)
def modifier_client(
    client_id: int,
    demande: DemandeClient,
    request: Request,
    session: Session = Depends(exiger_role("responsable")),
):
    bd = obtenir_bd(request)
    with bd.connexion_pour(role_pg(session.role), utilisateur_id=session.utilisateur_id) as conn:
        with conn.cursor() as cur:
            _client(cur, client_id)  # 404 si absent
            cur.execute(
                """
                UPDATE clients SET nom = %s, telephone = %s, plafond_credit = %s, site_id = %s
                 WHERE id = %s
                """,
                (demande.nom, demande.telephone, demande.plafond_credit, demande.site_id, client_id),
            )
            ligne = _client(cur, client_id)
    return ligne


@routeur.patch("/{client_id}/actif", response_model=ReponseClient)
def changer_actif_client(
    client_id: int,
    demande: DemandeActifCompte,
    request: Request,
    session: Session = Depends(exiger_role("responsable")),
):
    """Désactiver un client n'efface rien : ses créances passées restent
    visibles et il peut toujours régler ce qu'il doit déjà (voir
    ``enregistrer_reglement_creance``, qui ne vérifie jamais ``actif``).
    Seule une NOUVELLE vente à crédit lui est refusée une fois désactivé."""
    bd = obtenir_bd(request)
    with bd.connexion_pour(role_pg(session.role), utilisateur_id=session.utilisateur_id) as conn:
        with conn.cursor() as cur:
            _client(cur, client_id)  # 404 si absent
            cur.execute("UPDATE clients SET actif = %s WHERE id = %s", (demande.actif, client_id))
            ligne = _client(cur, client_id)
    return ligne


@routeur.post(
    "/{client_id}/reglements",
    response_model=ReponseReglementCreance,
    status_code=status.HTTP_201_CREATED,
)
def enregistrer_reglement(
    client_id: int,
    demande: DemandeReglementCreance,
    request: Request,
    session: Session = Depends(exiger_role("responsable", "agent_comptabilite")),
):
    bd = obtenir_bd(request)
    with bd.connexion_pour(role_pg(session.role), utilisateur_id=session.utilisateur_id) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "SELECT enregistrer_reglement_creance("
                    "%s::integer, %s::numeric, %s::integer, %s::varchar) AS encours",
                    (client_id, demande.montant, session.utilisateur_id, demande.motif),
                )
            except (psycopg.errors.ForeignKeyViolation, psycopg.errors.CheckViolation) as exc:
                raise erreur_metier(exc) from exc
            encours = cur.fetchone()["encours"]
    return ReponseReglementCreance(client_id=client_id, encours=float(encours))
