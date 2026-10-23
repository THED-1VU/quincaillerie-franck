"""Décision D4 (cycle 75, 2026-10-23) — seuil de remises fixé à 10 % :
au-delà, validation obligatoire du responsable, VÉRIFIÉE CÔTÉ SERVEUR
(migration 051 active le mécanisme 037 resté inactif tant que le paramètre
valait 'a_definir').

Cas exigés par l'ordre du cycle 75 : 0 %, 10 % (limite, passe), 10,01 %
(refuse un agent, accepte un responsable), remise négative (refusée par
les contraintes SQL), contournement (prix négocié au-dessus du catalogue
= remise 0, jamais un crédit de remise ; remise globale soumise au même
seuil). L'autorisation est « journalisée » par conception : la vente qui
passe porte son auteur dans ventes.utilisateur_id (compte authentifié,
décision D9) et le détail exact prix_catalogue/remise_montant par ligne.
"""

from __future__ import annotations

from decimal import Decimal
import psycopg

from conftest import (
    MOT_DE_PASSE_AGENT_COMPTA,
    MOT_DE_PASSE_RESPONSABLE,
    PG_ADMIN_DSN,
    entete_autorisation,
    se_connecter,
)

_PRIX_CATALOGUE = 6500  # article 1 (Ciment CIM II 50 kg, site 1)


def _vente(
    numero: str, lignes: list[dict], remise_globale_pct: float | None = None, site_id: int | None = None
) -> dict:
    corps = {
        "mode_paiement": "especes",
        "numero_facturier": numero,
        "vendeur_id": 1,
        "lignes": lignes,
    }
    if remise_globale_pct is not None:
        corps["remise_globale_pct"] = remise_globale_pct
    if site_id is not None:
        corps["site_id"] = site_id
    return corps


def _remise_ligne_db(vente_id: int) -> tuple[int, int]:
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT prix_catalogue, remise_montant FROM ventes_lignes WHERE vente_id = %s",
                (vente_id,),
            )
            return cur.fetchone()


def test_remise_zero_pct_passee_par_un_agent(client):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json=_vente("MAG-D4A001", [{"article_id": 1, "quantite": 1, "remise_pct": 0}]),
    )
    assert reponse.status_code == 201, reponse.text


def test_remise_dix_pct_exacte_passee_par_un_agent(client):
    """La limite EST le seuil : strictement supérieur déclenche, 10 % exact
    passe pour tout compte autorisé (décision D4 : « jusqu'à 10 % »)."""
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json=_vente("MAG-D4A002", [{"article_id": 1, "quantite": 1, "remise_pct": 10}]),
    )
    assert reponse.status_code == 201, reponse.text
    vente_id = reponse.json()["vente_id"]
    catalogue, remise = _remise_ligne_db(vente_id)
    assert catalogue == _PRIX_CATALOGUE
    assert remise == 650  # 10 % de 6500


def test_remise_dix_pourcent_un_refusee_a_un_agent(client):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json=_vente("MAG-D4A003", [{"article_id": 1, "quantite": 1, "remise_pct": 10.01}]),
    )
    assert reponse.status_code == 403, reponse.text
    assert "responsable" in reponse.json()["detail"].lower()


def test_remise_dix_pourcent_un_acceptee_au_responsable(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json=_vente(
            "MAG-D4B001", [{"article_id": 1, "quantite": 1, "remise_pct": 10.01}], site_id=1
        ),
    )
    assert reponse.status_code == 201, reponse.text
    _, remise = _remise_ligne_db(reponse.json()["vente_id"])
    assert remise == Decimal("650.65")  # 10,01 % de 6500, arrondi arithmétique


def test_remise_globale_supérieure_refusee_a_un_agent(client):
    """La remise de la vente ENTIÈRE (mécanisme séparé, 037) est soumise au
    même seuil — un agent ne peut pas la contourner en la déplaçant de la
    ligne vers la vente."""
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json=_vente(
            "MAG-D4A004",
            [{"article_id": 1, "quantite": 2, "remise_pct": 0}],
            remise_globale_pct=15,
        ),
    )
    assert reponse.status_code == 403, reponse.text


def test_remise_negative_refusee_par_le_serveur(client):
    """Une remise négative (montant < 0) contredit la contrainte SQL
    chk_ventes_lignes_remise_coherente (remise = GREATEST(catalogue - prix, 0))
    — refusée, jamais convertie en majoration déguisée."""
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json=_vente("MAG-D4A005", [{"article_id": 1, "quantite": 1, "remise_montant": -100}]),
    )
    assert reponse.status_code == 422, reponse.text


def test_prix_negocie_au_dessus_du_catalogue_nest_pas_une_remise(client):
    """Contournement : un prix négocié AU-DESSUS du catalogue est légitime
    (point d) mais n'enregistre JAMAIS une remise négative — la remise vaut
    0 (GREATEST), aucun crédit de remise reportable n'est créé."""
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json=_vente("MAG-D4A006", [{"article_id": 1, "quantite": 1, "prix_unitaire": 7000}]),
    )
    assert reponse.status_code == 201, reponse.text
    _, remise = _remise_ligne_db(reponse.json()["vente_id"])
    assert remise == 0
