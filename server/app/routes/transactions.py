"""Recettes et dépenses hors vente (chantier C6, cycle 16).

Une vente crée déjà sa propre recette automatiquement, dans la même
transaction que le décrément de stock (``routes/ventes.py``, cycle 6) —
`POST /transactions` sert exclusivement aux mouvements de caisse HORS
vente (dépenses, recettes diverses), jamais à en créer une seconde pour
une vente déjà enregistrée (l'index unique partiel du cycle 2 le
refuserait de toute façon).

Hors périmètre, volontairement : clôture de caisse (addendum, point g,
non tranché) — cette route enregistre une transaction datée et attribuée,
elle ne rapproche rien avec un comptage d'espèces en caisse. Aucune règle
de rapprochement n'est inventée ici.
"""

from __future__ import annotations

from datetime import date as _date

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..deps import exiger_role, obtenir_bd
from ..erreurs import erreur_metier
from ..roles import role_pg
from ..schemas import DemandeTransaction, ReponseTransaction
from ..securite import Session

routeur = APIRouter(prefix="/transactions", tags=["transactions"])


@routeur.post("", response_model=ReponseTransaction, status_code=status.HTTP_201_CREATED)
def enregistrer_transaction(
    demande: DemandeTransaction,
    request: Request,
    session: Session = Depends(exiger_role("responsable", "agent_comptabilite")),
):
    if session.site_id is not None:
        site_cible = session.site_id
    elif demande.site_id is not None:
        site_cible = demande.site_id
    else:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Le site est obligatoire pour un compte responsable.",
        )

    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=site_cible, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO transactions (site_id, utilisateur_id, type, montant, description, employe_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        site_cible, session.utilisateur_id, demande.type,
                        demande.montant, demande.description, demande.employe_id,
                    ),
                )
                transaction_id = cur.fetchone()["id"]
            except psycopg.errors.ForeignKeyViolation as exc:
                raise erreur_metier(exc) from exc

    return ReponseTransaction(
        transaction_id=transaction_id, site_id=site_cible, type=demande.type,
        montant=demande.montant, description=demande.description, employe_id=demande.employe_id,
    )


@routeur.get("")
def lister_transactions(
    date_debut: str,
    date_fin: str,
    request: Request,
    session: Session = Depends(exiger_role("responsable", "agent_comptabilite")),
):
    """Historique filtrable par période — le site vient de la RLS
    (`p_transactions_site`, cycle 1) : un responsable voit les deux sites,
    un agent comptabilité seulement le sien, sans qu'aucun paramètre de
    site ne soit accepté ici."""
    try:
        debut = _date.fromisoformat(date_debut)
        fin = _date.fromisoformat(date_fin)
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "date_debut et date_fin doivent être au format AAAA-MM-JJ.",
        ) from exc
    if debut > fin:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "date_debut ne peut pas être postérieure à date_fin.",
        )

    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, site_id, type, montant, description, employe_id, vente_id, date_transaction
                  FROM transactions
                 WHERE date_transaction::date BETWEEN %s AND %s
                 ORDER BY date_transaction DESC
                """,
                (debut, fin),
            )
            lignes = cur.fetchall()

    return {"transactions": lignes}
