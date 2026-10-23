"""Décision D9 (cycle 75, 2026-10-23) — l'encaissement est attribué au
compte AUTHENTIFIÉ, jamais au « premier responsable trouvé » (écart C5-01,
constat chiffré du cycle 66).

Trois preuves :
  * un agent_comptabilite qui saisit une vente en devient l'encaisseur
    (`ventes.utilisateur_caisse_id`) — c'était le défaut corrigé ;
  * le responsable qui saisit en est l'encaisseur (cas trivial, jamais
    régressé) ;
  * une tentative d'INJECTION du champ depuis le navigateur est ignorée :
    DemandeVente n'expose aucun champ d'encaisseur, l'identifiant vient du
    seul jeton signé — la vente passe et l'encaisseur reste l'authentifié.
"""

from __future__ import annotations

import psycopg

from conftest import (
    MOT_DE_PASSE_AGENT_COMPTA,
    MOT_DE_PASSE_RESPONSABLE,
    PG_ADMIN_DSN,
    entete_autorisation,
    se_connecter,
)


def _encaisseur(vente_id: int) -> tuple[int, str]:
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(
                """
                SELECT u.id, u.identifiant
                  FROM ventes v JOIN utilisateurs u ON u.id = v.utilisateur_caisse_id
                 WHERE v.id = %s
                """,
                (vente_id,),
            )
            ligne = cur.fetchone()
            assert ligne is not None, "Vente payée sans encaisseur (prevol.sql:36)"
            return ligne["id"], ligne["identifiant"]


def _id_utilisateur(identifiant: str) -> int:
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM utilisateurs WHERE identifiant = %s", (identifiant,))
            return cur.fetchone()[0]


def test_encaissement_attribue_a_lagent_qui_saisit(client):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json={
            "mode_paiement": "especes",
            "numero_facturier": "MAG-D90001",
            "vendeur_id": 1,
            "lignes": [{"article_id": 1, "quantite": 1, "prix_unitaire": 6500}],
        },
    )
    assert reponse.status_code == 201, reponse.text
    vente_id = reponse.json()["vente_id"]

    id_agent = _id_utilisateur("magasin.compta")
    id_encaisseur, identifiant_encaisseur = _encaisseur(vente_id)
    assert (id_encaisseur, identifiant_encaisseur) == (id_agent, "magasin.compta")


def test_encaissement_responsable_lui_meme(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json={
            "mode_paiement": "especes",
            "site_id": 1,
            "numero_facturier": "MAG-D90002",
            "vendeur_id": 1,
            "lignes": [{"article_id": 1, "quantite": 1, "prix_unitaire": 6500}],
        },
    )
    assert reponse.status_code == 201, reponse.text
    vente_id = reponse.json()["vente_id"]

    id_resp = _id_utilisateur("resp")
    id_encaisseur, identifiant_encaisseur = _encaisseur(vente_id)
    assert (id_encaisseur, identifiant_encaisseur) == (id_resp, "resp")


def test_injection_du_champ_encaisseur_depuis_le_navigateur_ignoree(client):
    """Résistance à l'usurpation : le client tente d'imposer l'encaisseur
    (celui d'un autre compte) dans le corps JSON — le schéma de la demande
    n'expose pas ce champ, la valeur injectée est ignorée et l'encaisseur
    reste le compte authentifié (jeton signé)."""
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    id_resp = _id_utilisateur("resp")
    assert id_resp != _id_utilisateur("magasin.compta")

    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json={
            "mode_paiement": "especes",
            "numero_facturier": "MAG-D90003",
            "vendeur_id": 1,
            "lignes": [{"article_id": 1, "quantite": 1, "prix_unitaire": 6500}],
            "utilisateur_caisse_id": id_resp,
        },
    )
    assert reponse.status_code == 201, reponse.text
    vente_id = reponse.json()["vente_id"]

    id_agent = _id_utilisateur("magasin.compta")
    id_encaisseur, identifiant_encaisseur = _encaisseur(vente_id)
    assert (id_encaisseur, identifiant_encaisseur) == (id_agent, "magasin.compta")
