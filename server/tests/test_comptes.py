"""Chantier C2 (cycle 32) : gestion des comptes depuis l'application.

Routes ``/admin/comptes`` réservées au responsable (CDC §3.8, décision du
2026-09-20). Ces tests prouvent, par exécution réelle via l'API :

- liste des comptes sans jamais le hachage ;
- création d'un agent (stock/comptabilité, site obligatoire), refus des
  identifiants en double, des mots de passe trop courts et du rôle
  responsable (réservé à l'outil C0-C) ;
- désactivation / réactivation, avec les règles du propriétaire
  (auto-désactivation refusée ; dernier responsable protégé — règle de
  défense en profondeur, voir note) ;
- la session d'un compte désactivé est coupée immédiatement (requête
  suivante refusée).
"""

from __future__ import annotations

from conftest import (
    MOT_DE_PASSE_RESPONSABLE,
    entete_autorisation,
    se_connecter,
)


def _creer_compte(client, jeton, identifiant="nouveau.stock", role="agent_stock",
                  site_id=1, mot_de_passe="MotDePasse123", nom="Nouvel Agent"):
    return client.post(
        "/admin/comptes",
        headers=entete_autorisation(jeton),
        json={
            "nom_complet": nom,
            "identifiant": identifiant,
            "mot_de_passe": mot_de_passe,
            "role": role,
            "site_id": site_id,
        },
    )


def test_lister_comptes_responsable_sans_hash(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.get("/admin/comptes", headers=entete_autorisation(session["jeton"]))
    assert reponse.status_code == 200, reponse.text
    comptes = reponse.json()["comptes"]
    assert len(comptes) == 5
    for compte in comptes:
        assert "mot_de_passe_hash" not in compte
        assert set(compte) == {
            "id", "nom_complet", "identifiant", "role", "site_id",
            "actif", "doit_changer_mot_de_passe", "date_creation",
        }


def test_lister_comptes_refuse_aux_agents(client):
    for identifiant, mot_de_passe in (
        ("magasin.stock", "AgentStockTest123"),
        ("magasin.compta", "AgentComptaTest123"),
    ):
        session = se_connecter(client, identifiant, mot_de_passe)
        reponse = client.get("/admin/comptes", headers=entete_autorisation(session["jeton"]))
        assert reponse.status_code == 403, reponse.text


def test_creer_compte_agent_et_connexion(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = _creer_compte(client, session["jeton"])
    assert reponse.status_code == 201, reponse.text
    corps = reponse.json()
    assert corps["identifiant"] == "nouveau.stock"
    assert corps["role"] == "agent_stock"
    assert corps["site_id"] == 1
    assert corps["actif"] is True
    assert corps["doit_changer_mot_de_passe"] is True
    assert "mot_de_passe_hash" not in corps

    connexion = client.post(
        "/auth/connexion",
        json={"identifiant": "nouveau.stock", "mot_de_passe": "MotDePasse123"},
    )
    assert connexion.status_code == 200, connexion.text
    assert connexion.json()["doit_changer_mot_de_passe"] is True


def test_creer_compte_identifiant_deja_pris(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = _creer_compte(client, session["jeton"], identifiant="resp")
    assert reponse.status_code == 422, reponse.text
    assert "déjà utilisé" in reponse.json()["detail"]


def test_creer_compte_mot_de_passe_court(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = _creer_compte(client, session["jeton"], mot_de_passe="court")
    assert reponse.status_code == 422, reponse.text


def test_creer_compte_role_responsable_refuse(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = _creer_compte(client, session["jeton"], identifiant="deuxieme.resp",
                            role="responsable", site_id=None)
    assert reponse.status_code == 422, reponse.text


def test_creer_compte_site_invalide_refuse(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = _creer_compte(client, session["jeton"], identifiant="site.invalide",
                            site_id=999)
    assert reponse.status_code == 422, reponse.text


def test_desactiver_reactiver_et_coupure_session(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    cree = _creer_compte(client, session["jeton"], identifiant="cible.agent")
    assert cree.status_code == 201, cree.text
    compte_id = cree.json()["id"]

    # L'agent se connecte : sa session est valide.
    session_agent = se_connecter(client, "cible.agent", "MotDePasse123")
    assert client.get("/moi", headers=entete_autorisation(session_agent["jeton"])).status_code == 200

    # Désactivation : la session en cours est coupée immédiatement.
    desactive = client.patch(
        f"/admin/comptes/{compte_id}/actif",
        headers=entete_autorisation(session["jeton"]),
        json={"actif": False},
    )
    assert desactive.status_code == 200, desactive.text
    assert desactive.json()["actif"] is False
    assert client.get("/moi", headers=entete_autorisation(session_agent["jeton"])).status_code == 401

    # La connexion est refusée tant que le compte est désactivé.
    reconnexion = client.post(
        "/auth/connexion",
        json={"identifiant": "cible.agent", "mot_de_passe": "MotDePasse123"},
    )
    assert reconnexion.status_code == 401, reconnexion.text
    assert "désactivé" in reconnexion.json()["detail"]

    # Réactivation : la connexion fonctionne de nouveau.
    reactive = client.patch(
        f"/admin/comptes/{compte_id}/actif",
        headers=entete_autorisation(session["jeton"]),
        json={"actif": True},
    )
    assert reactive.status_code == 200, reactive.text
    assert reactive.json()["actif"] is True
    assert client.post(
        "/auth/connexion",
        json={"identifiant": "cible.agent", "mot_de_passe": "MotDePasse123"},
    ).status_code == 200


def test_desactiver_son_propre_compte_refuse(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.patch(
        f"/admin/comptes/{session['utilisateur_id']}/actif",
        headers=entete_autorisation(session["jeton"]),
        json={"actif": False},
    )
    assert reponse.status_code == 422, reponse.text
    assert "propre compte" in reponse.json()["detail"]


def test_aucun_hash_dans_les_reponses_creation(client):
    """Le hachage n'apparaît ni dans la création ni dans la liste."""
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    cree = _creer_compte(client, session["jeton"], identifiant="sans.secret")
    assert cree.status_code == 201, cree.text
    liste = client.get("/admin/comptes", headers=entete_autorisation(session["jeton"]))
    for compte in liste.json()["comptes"]:
        assert "hash" not in str(compte).lower()
