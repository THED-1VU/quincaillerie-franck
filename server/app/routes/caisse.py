"""Clôture de caisse quotidienne, PAR SITE (chantier C6, addendum point g,
décidé le 2026-09-13).

Réservée au responsable — même périmètre que la RH (``routes/rh.py``) :
rémunération et caisse sont des données au moins aussi sensibles (CDC §3.5).
Ni l'agent stock ni l'agent comptabilité n'ont le moindre droit sur
``clotures_caisse`` ni sur ``cloturer_caisse()`` (migration 019, aucun GRANT).

Tout le calcul (attendu par mode de paiement, écart) est fait par la fonction
PostgreSQL ``cloturer_caisse()`` — cette route ne fait que transmettre la
demande et relayer le résultat, jamais recalculer quoi que ce soit elle-même.
"""

from __future__ import annotations

from datetime import date as _date

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..deps import exiger_role, obtenir_bd
from ..erreurs import erreur_metier
from ..roles import role_pg
from ..schemas import DemandeClotureCaisse, ReponseClotureCaisse
from ..securite import Session

routeur = APIRouter(prefix="/caisse", tags=["caisse"])


@routeur.get("/attendu")
def attendu_du_jour(
    site_id: int,
    date_cloture: str,
    request: Request,
    session: Session = Depends(exiger_role("responsable")),
):
    """Prévisualisation, AVANT toute saisie de comptage : l'addendum (point g)
    décrit « le système affiche le total attendu » puis « le responsable
    saisit les espèces comptées » — deux étapes distinctes. Route en LECTURE
    SEULE (``calculer_attendu_caisse``, migration 019, pas SECURITY DEFINER) :
    ne crée aucune clôture, ne fige rien."""
    try:
        jour = _date.fromisoformat(date_cloture)
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "date_cloture doit être au format AAAA-MM-JJ.",
        ) from exc

    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT especes, orange_money, mtn_momo, autre FROM calculer_attendu_caisse(%s, %s)",
                (site_id, jour),
            )
            ligne = cur.fetchone()

    return {
        "site_id": site_id,
        "date_cloture": jour,
        "attendu_especes": ligne["especes"],
        "attendu_orange_money": ligne["orange_money"],
        "attendu_mtn_momo": ligne["mtn_momo"],
        "attendu_autre": ligne["autre"],
    }


def _ligne_vers_reponse(ligne: dict) -> ReponseClotureCaisse:
    return ReponseClotureCaisse(
        cloture_id=ligne["id"],
        site_id=ligne["site_id"],
        date_cloture=ligne["date_cloture"],
        attendu_especes=ligne["attendu_especes"],
        attendu_orange_money=ligne["attendu_orange_money"],
        attendu_mtn_momo=ligne["attendu_mtn_momo"],
        attendu_autre=ligne["attendu_autre"],
        compte_especes=ligne["compte_especes"],
        compte_orange_money=ligne["compte_orange_money"],
        compte_mtn_momo=ligne["compte_mtn_momo"],
        compte_autre=ligne["compte_autre"],
        ecart_especes=ligne["ecart_especes"],
        ecart_orange_money=ligne["ecart_orange_money"],
        ecart_mtn_momo=ligne["ecart_mtn_momo"],
        ecart_autre=ligne["ecart_autre"],
        commentaire=ligne["commentaire"],
        utilisateur_id=ligne["utilisateur_id"],
        cloture_rectificative_de=ligne["cloture_rectificative_de"],
    )


@routeur.post("", response_model=ReponseClotureCaisse, status_code=status.HTTP_201_CREATED)
def cloturer(
    demande: DemandeClotureCaisse,
    request: Request,
    session: Session = Depends(exiger_role("responsable")),
):
    """``site_id`` obligatoire (le responsable voit les deux sites — même
    principe que pour une vente ou une transaction) ; l'attendu et l'écart ne
    viennent JAMAIS du corps de la requête, seule ``cloturer_caisse()`` les
    calcule (migration 019)."""
    if demande.site_id is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Le site est obligatoire pour une clôture de caisse.",
        )

    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=demande.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    SELECT * FROM cloturer_caisse(
                        %(site_id)s::INTEGER, %(date_cloture)s::DATE,
                        %(espece_comptee)s::NUMERIC, %(utilisateur_id)s::INTEGER,
                        %(orange_money_compte)s::NUMERIC, %(mtn_momo_compte)s::NUMERIC,
                        %(autre_compte)s::NUMERIC, %(commentaire)s::VARCHAR,
                        %(cloture_rectificative_de)s::INTEGER
                    )
                    """,
                    {
                        "site_id": demande.site_id,
                        "date_cloture": demande.date_cloture,
                        "espece_comptee": demande.espece_comptee,
                        "utilisateur_id": session.utilisateur_id,
                        "orange_money_compte": demande.orange_money_compte,
                        "mtn_momo_compte": demande.mtn_momo_compte,
                        "autre_compte": demande.autre_compte,
                        "commentaire": demande.commentaire,
                        "cloture_rectificative_de": demande.cloture_rectificative_de,
                    },
                )
            except (
                psycopg.errors.CheckViolation,
                psycopg.errors.UniqueViolation,
                psycopg.errors.ForeignKeyViolation,
            ) as exc:
                raise erreur_metier(exc) from exc
            ligne = cur.fetchone()

    return _ligne_vers_reponse(ligne)


@routeur.get("")
def lister_clotures(
    request: Request,
    session: Session = Depends(exiger_role("responsable")),
):
    """Historique des clôtures — le site vient de la RLS (``p_clotures_caisse_
    site``, migration 019) : un responsable voit les deux sites, sans
    qu'aucun paramètre de site ne soit accepté ici (même principe que
    ``GET /transactions``)."""
    bd = obtenir_bd(request)
    with bd.connexion_pour(role_pg(session.role), utilisateur_id=session.utilisateur_id) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, site_id, date_cloture,
                       attendu_especes, attendu_orange_money, attendu_mtn_momo, attendu_autre,
                       compte_especes, compte_orange_money, compte_mtn_momo, compte_autre,
                       ecart_especes, ecart_orange_money, ecart_mtn_momo, ecart_autre,
                       commentaire, utilisateur_id, cloture_rectificative_de, date_creation
                  FROM clotures_caisse
                 ORDER BY date_cloture DESC, site_id, date_creation DESC
                """
            )
            lignes = cur.fetchall()

    return {"clotures": [_ligne_vers_reponse(ligne) for ligne in lignes]}
