"""Saisies aberrantes sur `POST /ventes` et conflits de transaction : un refus
de saisie est un 422 lisible, un conflit transactionnel un 409 « recommencez »
— jamais un 500 « Erreur interne » ni un faux « système injoignable ».

Constats de l'audit indépendant du 2026-10-23 (fuzz de l'API sur la base issue
des migrations 000→054) : 2,5 sacs de ciment, ou un prix de 10^15 FCFA, donnaient
« Erreur interne. » ; un interblocage PostgreSQL était présenté comme une
panne de la base.
"""

from __future__ import annotations

import psycopg
import pytest

from conftest import (
    MOT_DE_PASSE_AGENT_COMPTA,
    PG_ADMIN_DSN,
    entete_autorisation,
    se_connecter,
)


def _stock_ciment() -> float:
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        return float(
            conn.execute(
                "SELECT quantite_stock FROM stocks_sites WHERE article_id = 1 AND site_id = 1"
            ).fetchone()[0]
        )


def _vente(client, jeton: str, numero: str, quantite, prix):
    return client.post(
        "/ventes",
        headers=entete_autorisation(jeton),
        json={
            "numero_facturier": numero,
            "vendeur_id": 1,
            "mode_paiement": "especes",
            "lignes": [{"article_id": 1, "quantite": quantite, "prix_unitaire": prix}],
        },
    )


@pytest.fixture()
def jeton(client) -> str:
    return se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)["jeton"]


def test_quantite_decimale_sur_article_entier_est_refusee_en_422(client, jeton):
    stock_avant = _stock_ciment()
    reponse = _vente(client, jeton, "MAG-ABE001", 2.5, 6500)
    assert reponse.status_code == 422, reponse.text
    assert "entières" in reponse.json()["detail"]
    assert _stock_ciment() == stock_avant


def test_quantite_arrondie_a_zero_est_refusee_sans_fuite_sql(client, jeton):
    reponse = _vente(client, jeton, "MAG-ABE002", 0.0001, 6500)
    assert reponse.status_code == 422, reponse.text
    detail = reponse.json()["detail"]
    assert "violates" not in detail and "ventes_lignes" not in detail  # règle C11


def test_prix_hors_capacite_est_refuse_en_422(client, jeton):
    reponse = _vente(client, jeton, "MAG-ABE003", 1, 1e15)
    assert reponse.status_code == 422, reponse.text
    assert "limite" in reponse.json()["detail"]


def test_entree_de_stock_hors_capacite_est_refusee_en_422(client):
    jeton_stock = se_connecter(client, "magasin.stock", "AgentStockTest123")["jeton"]
    reponse = client.post(
        "/stock/entrees",
        headers=entete_autorisation(jeton_stock),
        json={"article_id": 1, "quantite": 1e12},
    )
    assert reponse.status_code == 422, reponse.text


def test_interblocage_postgresql_est_un_409_et_non_une_panne(client, jeton, monkeypatch):
    class _BdQuiSeBloque:
        def connexion_pour(self, *args, **kwargs):
            raise psycopg.errors.DeadlockDetected("deadlock detected")

    monkeypatch.setattr("app.routes.ventes.obtenir_bd", lambda request: _BdQuiSeBloque())
    reponse = _vente(client, jeton, "MAG-ABE004", 1, 6500)
    assert reponse.status_code == 409, reponse.text
    detail = reponse.json()["detail"]
    assert "recommencez" in detail
    assert "injoignable" not in detail and "joindre" not in detail
