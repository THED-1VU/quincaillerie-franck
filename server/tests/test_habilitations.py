"""Tests d'habilitations (chantier C3) — pour chaque route, un test par rôle,
qui inspecte le CONTENU de la réponse (pas seulement le code HTTP) : un
agent stock ne doit voir AUCUN prix, un comptable AUCUNE quantité en stock,
même si le code de la route avait un bug.
"""

from __future__ import annotations

from conftest import (
    MOT_DE_PASSE_AGENT_COMPTA,
    MOT_DE_PASSE_AGENT_STOCK,
    MOT_DE_PASSE_RESPONSABLE,
    entete_autorisation,
    se_connecter,
)

CHAMPS_PRIX = {"prix_achat", "prix_vente"}
CHAMPS_STOCK = {"quantite_stock", "seuil_alerte"}


def _articles(client, identifiant, mot_de_passe):
    session = se_connecter(client, identifiant, mot_de_passe)
    reponse = client.get("/articles", headers=entete_autorisation(session["jeton"]))
    assert reponse.status_code == 200
    return reponse.json()["articles"], session


def test_agent_stock_ne_voit_aucun_prix(client):
    articles, _ = _articles(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    assert len(articles) > 0, "le jeu d'essai doit contenir au moins un article du site 1"
    for article in articles:
        champs_presents = set(article.keys())
        interdits = champs_presents & CHAMPS_PRIX
        assert not interdits, f"champ(s) de prix présent(s) pour l'agent stock : {interdits}"
        # Les champs attendus, eux, sont bien là.
        assert "quantite_stock" in article
        assert "seuil_alerte" in article


def test_agent_comptabilite_ne_voit_aucune_quantite(client):
    articles, _ = _articles(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    assert len(articles) > 0
    for article in articles:
        champs_presents = set(article.keys())
        interdits = champs_presents & CHAMPS_STOCK
        assert not interdits, f"champ(s) de stock présent(s) pour la comptabilité : {interdits}"
        assert "prix_vente" in article
        assert "prix_achat" not in article  # seul le responsable voit le prix d'achat


def test_responsable_voit_tout(client):
    articles, _ = _articles(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    assert len(articles) > 0
    premier = articles[0]
    for champ in ("prix_achat", "prix_vente", "quantite_stock", "seuil_alerte"):
        assert champ in premier, f"le responsable doit voir {champ}"


def test_responsable_voit_les_deux_sites(client):
    articles, _ = _articles(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    sites_vus = {a["site_id"] for a in articles}
    assert sites_vus == {1, 2}, f"le responsable doit voir les deux sites, a vu : {sites_vus}"


def test_agent_stock_ne_voit_que_son_site(client):
    articles, _ = _articles(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    sites_vus = {a["site_id"] for a in articles}
    assert sites_vus == {1}, f"l'agent du Magasin ne doit voir que le site 1, a vu : {sites_vus}"


def test_agent_comptabilite_ne_voit_que_son_site(client):
    articles, _ = _articles(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    sites_vus = {a["site_id"] for a in articles}
    assert sites_vus == {1}, f"le comptable du Magasin ne doit voir que le site 1, a vu : {sites_vus}"


def test_agent_stock_interdit_sur_synthese_ventes(client):
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.get(
        "/ventes/synthese-jour", headers=entete_autorisation(session["jeton"])
    )
    assert reponse.status_code == 403


def test_comptabilite_et_responsable_autorises_sur_synthese_ventes(client):
    for identifiant, mdp in (
        ("magasin.compta", MOT_DE_PASSE_AGENT_COMPTA),
        ("resp", MOT_DE_PASSE_RESPONSABLE),
    ):
        session = se_connecter(client, identifiant, mdp)
        reponse = client.get(
            "/ventes/synthese-jour", headers=entete_autorisation(session["jeton"])
        )
        assert reponse.status_code == 200, f"{identifiant} devrait pouvoir accéder à cette route"


def test_profil_ne_renvoie_jamais_de_hachage(client):
    for identifiant, mdp in (
        ("resp", MOT_DE_PASSE_RESPONSABLE),
        ("magasin.stock", MOT_DE_PASSE_AGENT_STOCK),
        ("magasin.compta", MOT_DE_PASSE_AGENT_COMPTA),
    ):
        session = se_connecter(client, identifiant, mdp)
        reponse = client.get("/moi", headers=entete_autorisation(session["jeton"]))
        assert reponse.status_code == 200
        assert "hash" not in reponse.text.lower()
        assert "$2a$" not in reponse.text
        assert reponse.json()["utilisateur_id"] == session["utilisateur_id"]


def test_aucune_route_accessible_sans_jeton(client):
    for methode, chemin in (
        ("get", "/articles"),
        ("get", "/ventes/synthese-jour"),
        ("get", "/moi"),
        ("post", "/auth/changer-mot-de-passe"),
        ("post", "/admin/comptes/1/deverrouiller"),
    ):
        reponse = getattr(client, methode)(chemin)
        assert reponse.status_code == 401, f"{methode.upper()} {chemin} devrait exiger un jeton"


def test_jeton_invalide_refuse(client):
    reponse = client.get("/moi", headers={"Authorization": "Bearer ceci-nest-pas-un-jeton-valide"})
    assert reponse.status_code == 401


def test_jeton_falsifie_refuse(client):
    """Un jeton dont on a changé un caractère (donc la signature ne
    correspond plus) doit être rejeté — preuve que la signature EST
    vérifiée, pas seulement décodée."""
    session = se_connecter(client, "resp", "ResponsableTest123")
    jeton = session["jeton"]
    corps, signature = jeton.rsplit(".", 1)
    signature_alteree = ("a" if signature[0] != "a" else "b") + signature[1:]
    jeton_falsifie = f"{corps}.{signature_alteree}"

    reponse = client.get("/moi", headers=entete_autorisation(jeton_falsifie))
    assert reponse.status_code == 401
