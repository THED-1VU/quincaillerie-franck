"""Chantier C7 (inventaire et écarts) — cycle 7.

Prouve par exécution le principe absolu du comptage à l'aveugle, énoncé au
cycle 5 : la quantité que le système attend n'atteint JAMAIS le navigateur
de l'agent stock — ni dans la liste à compter, ni dans la réponse après
soumission, ni en contournant l'API pour interroger PostgreSQL directement
sous son rôle.
"""

from __future__ import annotations

import psycopg
import pytest

from conftest import (
    MOT_DE_PASSE_AGENT_COMPTA,
    MOT_DE_PASSE_AGENT_STOCK,
    MOT_DE_PASSE_RESPONSABLE,
    PG_ADMIN_DSN,
    entete_autorisation,
    se_connecter,
)


def test_liste_a_compter_ne_contient_aucune_quantite(client):
    """Ni quantite_stock, ni seuil_alerte, ni aucune autre colonne de stock
    ne doit apparaître dans la liste à compter — seulement id/nom/unité/site,
    et pour l'agent stock, toujours le même site que sa session."""
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.get(
        "/inventaire/articles-a-compter?moment=matin", headers=entete_autorisation(session["jeton"])
    )
    assert reponse.status_code == 200, reponse.text
    articles = reponse.json()["articles"]
    assert len(articles) > 0
    for a in articles:
        assert set(a.keys()) == {"id", "nom", "unite", "site_id"}, f"colonne inattendue : {a}"
        assert a["site_id"] == 1


def test_liste_a_compter_du_responsable_distingue_les_deux_sites(client):
    """Correction du contrôle de boucle après le cycle 7 : le responsable
    couvre les deux sites, la liste doit permettre de les distinguer."""
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.get(
        "/inventaire/articles-a-compter?moment=matin", headers=entete_autorisation(session["jeton"])
    )
    assert reponse.status_code == 200, reponse.text
    articles = reponse.json()["articles"]
    sites_presents = {a["site_id"] for a in articles}
    assert sites_presents == {1, 2}, f"le responsable devrait voir les deux sites, trouvé : {sites_presents}"


def test_comptage_ne_renvoie_jamais_quantite_attendue_ni_ecart(client):
    """La réponse à la soumission d'un comptage ne contient QUE ce que le
    client a lui-même envoyé."""
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    entetes = entete_autorisation(session["jeton"])

    reponse = client.post(
        "/inventaire/comptages",
        headers=entetes,
        json={"article_id": 1, "moment": "matin", "quantite_comptee": 25},
    )
    assert reponse.status_code == 201, reponse.text
    corps = reponse.json()
    assert set(corps.keys()) == {"comptage_id", "article_id", "moment", "quantite_comptee"}
    assert corps["quantite_comptee"] == 25
    assert "ecart" not in str(corps)  # ceinture et bretelles : absent même en texte brut
    assert "attendu" not in str(corps).lower()


def test_champs_interdits_injectes_par_le_client_sont_sans_effet(client):
    """Trouvé lors du contrôle de boucle après le cycle 7 (aucun test ne
    l'essayait avant) : un client qui injecte volontairement
    quantite_attendue/ecart dans le corps de la requête ne doit ni les voir
    dans la réponse (déjà couvert ci-dessus), ni leur voir le moindre effet
    en base — c'est la vraie valeur (le stock réel au moment du comptage)
    qui doit être enregistrée, jamais celle envoyée par le client."""
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    entetes = entete_autorisation(session["jeton"])

    # Article 1 "Ciment CIM II 50 kg" : stock réel 30 (jeu d'essai).
    reponse = client.post(
        "/inventaire/comptages",
        headers=entetes,
        json={
            "article_id": 1, "moment": "matin", "quantite_comptee": 25,
            "quantite_attendue": 999, "ecart": 0,
        },
    )
    assert reponse.status_code == 201, reponse.text
    corps = reponse.json()
    assert set(corps.keys()) == {"comptage_id", "article_id", "moment", "quantite_comptee"}

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(
                "SELECT quantite_attendue, ecart FROM comptages_stock WHERE id = %s",
                (corps["comptage_id"],),
            )
            ligne = cur.fetchone()
            assert ligne["quantite_attendue"] == 30, "la valeur injectée (999) n'aurait jamais dû être retenue"
            assert ligne["ecart"] == 25 - 30


@pytest.mark.parametrize("colonne", ["ecart", "quantite_attendue"])
def test_agent_stock_ne_peut_pas_lire_ecart_en_sql_direct(colonne):
    """Preuve la plus forte (comme pour prix_vente au cycle 2) : même en
    contournant complètement l'API, PostgreSQL refuse à l'agent stock la
    lecture de `ecart` et `quantite_attendue` (migration 012) — une
    connexion neuve par colonne, pour ne pas mélanger une transaction déjà
    avortée avec la suivante."""
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("SET ROLE qf_agent_stock")
            cur.execute("SELECT set_config('qf.site_id', '1', true)")
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                cur.execute(f"SELECT {colonne} FROM comptages_stock LIMIT 1")  # noqa: S608
        conn.rollback()  # remet la transaction avortée à plat avant la sortie du `with`


def test_article_deja_compte_disparait_de_la_liste_et_refuse_un_second_envoi(client):
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    entetes = entete_autorisation(session["jeton"])

    reponse = client.post(
        "/inventaire/comptages",
        headers=entetes,
        json={"article_id": 2, "moment": "soir", "quantite_comptee": 10},
    )
    assert reponse.status_code == 201, reponse.text

    # Un second comptage du même article, même moment, même jour -> refusé.
    reponse2 = client.post(
        "/inventaire/comptages",
        headers=entetes,
        json={"article_id": 2, "moment": "soir", "quantite_comptee": 12},
    )
    assert reponse2.status_code == 409, reponse2.text
    assert "déjà été compté" in reponse2.json()["detail"]

    # Il n'apparaît plus dans la liste à compter pour ce moment.
    liste = client.get("/inventaire/articles-a-compter?moment=soir", headers=entetes).json()["articles"]
    assert all(a["id"] != 2 for a in liste)


def test_agent_stock_ne_peut_pas_compter_un_article_de_lautre_site(client):
    """« Clou 5 cm » (id 3) appartient au Comptoir (site 2) ; l'agent du
    Magasin (site 1) ne peut pas le compter."""
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    entetes = entete_autorisation(session["jeton"])

    reponse = client.post(
        "/inventaire/comptages",
        headers=entetes,
        json={"article_id": 3, "moment": "matin", "quantite_comptee": 5},
    )
    assert reponse.status_code == 422, reponse.text
    assert "introuvable" in reponse.json()["detail"].lower()


def test_agent_comptabilite_interdit_sur_linventaire(client):
    """La comptabilité n'a d'ailleurs aucun droit sur comptages_stock
    (migration 008) : refusé avant même d'atteindre la base."""
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    entetes = entete_autorisation(session["jeton"])

    assert client.get("/inventaire/articles-a-compter?moment=matin", headers=entetes).status_code == 403
    assert client.post(
        "/inventaire/comptages", headers=entetes,
        json={"article_id": 1, "moment": "matin", "quantite_comptee": 1},
    ).status_code == 403


def test_ecarts_du_jour_reserves_au_responsable(client):
    session_agent = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    assert client.get(
        "/inventaire/ecarts", headers=entete_autorisation(session_agent["jeton"])
    ).status_code == 403

    # Article 1 "Ciment CIM II 50 kg" : stock réel 30, on en compte 22 -> écart -8.
    client.post(
        "/inventaire/comptages",
        headers=entete_autorisation(session_agent["jeton"]),
        json={"article_id": 1, "moment": "matin", "quantite_comptee": 22},
    )

    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.get("/inventaire/ecarts", headers=entete_autorisation(session_resp["jeton"]))
    assert reponse.status_code == 200, reponse.text
    ecarts = reponse.json()["ecarts"]
    assert len(ecarts) == 1
    assert ecarts[0]["article_nom"] == "Ciment CIM II 50 kg"
    assert ecarts[0]["quantite_comptee"] == 22
    assert ecarts[0]["quantite_attendue"] == 30
    assert ecarts[0]["ecart"] == -8


def test_ecarts_ventes_du_jour_relie_c5_et_c7(client):
    """Une vente à découvert de stock (chantier C5, addendum point e) doit
    apparaître dans les écarts de C7 — les deux chantiers partagent le même
    principe : jamais de blocage, toujours une trace pour le responsable."""
    session_compta = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    # "Article rare" (id 4, site 1, stock réel 1) : on en vend 3.
    reponse_vente = client.post(
        "/ventes",
        headers=entete_autorisation(session_compta["jeton"]),
        json={
            "mode_paiement": "especes",
            "lignes": [{"article_id": 4, "quantite": 3, "prix_unitaire": 2000}],
        },
    )
    assert reponse_vente.status_code == 201, reponse_vente.text
    vente_id = reponse_vente.json()["vente_id"]

    session_agent = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    assert client.get(
        "/inventaire/ecarts-ventes", headers=entete_autorisation(session_agent["jeton"])
    ).status_code == 403

    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.get("/inventaire/ecarts-ventes", headers=entete_autorisation(session_resp["jeton"]))
    assert reponse.status_code == 200, reponse.text
    ecarts = reponse.json()["ecarts"]
    assert len(ecarts) == 1
    assert ecarts[0]["article_nom"] == "Article rare"
    assert ecarts[0]["vente_id"] == vente_id
    assert ecarts[0]["quantite_manquante"] == 2
    assert ecarts[0]["regularise"] is False
