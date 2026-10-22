"""Obligation de changer le mot de passe provisoire (chantier C8, cycle 65).

Défaut trouvé par la matrice des rôles : ``doit_changer_mot_de_passe`` était
émis dans le jeton et dans la réponse de connexion, mais RIEN ne l'appliquait
— un compte fraîchement créé (ou réinitialisé par le responsable) pouvait
travailler indéfiniment avec son mot de passe provisoire, alors que
server/README.md (C2) documente une « obligation de changer le mot de passe
à la première connexion ».

Correctif vérifié ici :
- migration 050, fonction ``changement_mdp_requis()`` (fenêtre étroite
  accordée au seul qf_app, comme ``compte_est_actif`` en 024) ;
- ``deps.obtenir_session`` la relit EN BASE à chaque requête authentifiée
  (pas la valeur figée du jeton) et refuse tout sauf
  ``/auth/changer-mot-de-passe`` et ``/auth/deconnexion`` tant qu'elle est
  vraie. Relire la base fait passer la session dès le changement réussi, et
  coupe immédiatement un jeton encore valide après réinitialisation par le
  responsable (migration 033 repasse le drapeau à TRUE).
"""

from __future__ import annotations

from conftest import (
    MOT_DE_PASSE_AGENT_COMPTA,
    MOT_DE_PASSE_AGENT_STOCK,
    MOT_DE_PASSE_RESPONSABLE,
    entete_autorisation,
    fixer_drapeau_changement_mdp,
    se_connecter,
)


def _imposer_changement_mdp(identifiant: str) -> None:
    fixer_drapeau_changement_mdp(identifiant, True)


def test_mdp_provisoire_bloque_toutes_routes_sauf_deux(client):
    _imposer_changement_mdp("magasin.compta")
    connexion = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    assert connexion["doit_changer_mot_de_passe"] is True
    entetes = entete_autorisation(connexion["jeton"])

    # Chaque route métier est refusée avec le même message explicite, 403 —
    # y compris /moi (n'importe quel rôle authentifié) et une route réservée
    # au responsable (le contrôle de mot de passe provisoire précède le
    # contrôle de rôle).
    for methode, chemin in [
        ("GET", "/moi"),
        ("GET", "/articles"),
        ("GET", "/ventes/parametres"),
        ("GET", "/tableau-bord/alertes-stock"),
        ("POST", "/ventes"),
        ("GET", "/admin/comptes"),
    ]:
        reponse = getattr(client, methode.lower())(chemin, headers=entetes)
        assert reponse.status_code == 403, (methode, chemin, reponse.status_code)
        assert "mot de passe provisoire" in reponse.json()["detail"]

    # Déconnexion : toujours possible, sinon l'utilisateur serait piégé.
    reponse = client.post("/auth/deconnexion", headers=entetes)
    assert reponse.status_code == 204


def test_mdp_provisoire_mauvais_actuel_refuse_puis_changement_libere(client):
    _imposer_changement_mdp("magasin.compta")
    connexion = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    entetes = entete_autorisation(connexion["jeton"])

    # Mauvais mot de passe actuel : 401, et le compte reste bloqué.
    reponse = client.post(
        "/auth/changer-mot-de-passe",
        headers=entetes,
        json={
            "mot_de_passe_actuel": "mauvais-mot-de-passe",
            "nouveau_mot_de_passe": "NouveauTest456",
        },
    )
    assert reponse.status_code == 401
    assert client.get("/moi", headers=entetes).status_code == 403

    # Changement réussi : 204 — et la MÊME session redevient utilisable
    # immédiatement, car le drapeau est relu en base et non dans le jeton.
    reponse = client.post(
        "/auth/changer-mot-de-passe",
        headers=entetes,
        json={
            "mot_de_passe_actuel": MOT_DE_PASSE_AGENT_COMPTA,
            "nouveau_mot_de_passe": "NouveauTest456",
        },
    )
    assert reponse.status_code == 204
    reponse = client.get("/moi", headers=entetes)
    assert reponse.status_code == 200
    assert reponse.json()["doit_changer_mot_de_passe"] is False

    # Le nouveau mot de passe fonctionne à la connexion suivante, l'ancien
    # (provisoire) ne passe plus.
    assert client.post(
        "/auth/connexion",
        json={"identifiant": "magasin.compta", "mot_de_passe": "NouveauTest456"},
    ).status_code == 200
    assert client.post(
        "/auth/connexion",
        json={"identifiant": "magasin.compta", "mot_de_passe": MOT_DE_PASSE_AGENT_COMPTA},
    ).status_code == 401


def test_reinitialisation_responsable_coupe_jeton_encore_valide(client):
    connexion = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    entetes = entete_autorisation(connexion["jeton"])
    assert client.get("/moi", headers=entetes).status_code == 200

    # Le responsable réinitialise le mot de passe de l'agent : le drapeau
    # repasse à TRUE (migration 033) — la session en cours doit être coupée
    # dès la requête suivante, sans attendre l'expiration du jeton.
    jeton_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)["jeton"]
    reponse = client.patch(
        f"/admin/comptes/{connexion['utilisateur_id']}/mot-de-passe",
        headers=entete_autorisation(jeton_resp),
        json={"mot_de_passe": "TemporaireTest789"},
    )
    assert reponse.status_code == 200
    assert reponse.json()["doit_changer_mot_de_passe"] is True

    reponse = client.get("/moi", headers=entetes)
    assert reponse.status_code == 403
    assert "mot de passe provisoire" in reponse.json()["detail"]
