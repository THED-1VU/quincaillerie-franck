"""Cycle 75-E — décision D6 (validée 2026-10-23) : session limitée à
480 minutes, expiration et révocation VÉRIFIABLES par exécution.

La durée de 480 minutes est une décision du propriétaire (2026-09-22,
migration 033 : parametres.duree_session_minutes, lue à chaque connexion —
le config.ini ne sert que de repli). D6 la confirme ; ce qui restait à
PROUVER ici, et que rien ne couvrait encore :

  - le jeton réellement émi porte ``exp - iat = 480 * 60`` et un ``jti``
    révocable (32 hex, migration 018) ;
  - un jeton SIGNÉ CORRECTEMENT mais dont ``exp`` est passé est refusé par
    une route HTTP réelle (401 « expiré ») — la preuve unitaire existante
    (test_securite.py, durée 0 minute) ne passait pas la frontière HTTP ;
  - AUCUNE route de renouvellement/refresh n'existe : arriver au bout des
    480 minutes impose une reconnexion complète (re-vérification du mot de
    passe, du verrouillage, du drapeau de changement provisoire). C'est le
    choix de sécurité assumé — pas de jeton éternel.

La bascule éventuelle du paramètre de durée reste la décision C2-01
(ouverte) : D6 fixe la valeur, elle ne l'automatise pas.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import time

from conftest import MOT_DE_PASSE_RESPONSABLE, entete_autorisation, se_connecter

_CLE_TEST = b"0" * 64  # conftest.ConfigApi.secret_key


def _charge_du_jeton(jeton: str) -> dict:
    corps_b64 = jeton.split(".")[0]
    return json.loads(base64.urlsafe_b64decode(corps_b64 + "=" * (-len(corps_b64) % 4)))


def _jeton_expire_bien_signe() -> str:
    """Même schéma que securite.GestionnaireSessions (HMAC-SHA256,
    base64url sans remplissage), clé de test identique : un jeton que la
    signature ET le format acceptent, mais dont la validité est révolue —
    exactement ce que devient un jeton de 480 minutes une minute de trop."""
    maintenant = int(time.time())
    charge = {
        "uid": 1,
        "role": "responsable",
        "roles": ["responsable"],
        "site": None,
        "nom": "Responsable Test",
        "chg": False,
        "iat": maintenant - 481 * 60,
        "exp": maintenant - 1,
        "jti": "e" * 32,
    }
    corps = base64.urlsafe_b64encode(
        json.dumps(charge, separators=(",", ":")).encode("utf-8")
    ).rstrip(b"=")
    signature = hmac.new(_CLE_TEST, corps, hashlib.sha256).digest()
    return (corps + b"." + base64.urlsafe_b64encode(signature).rstrip(b"=")).decode("ascii")


def test_le_jeton_emis_porte_480_minutes_et_un_jti_revocable(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    assert session["expire_dans_secondes"] == 480 * 60

    charge = _charge_du_jeton(session["jeton"])
    assert charge["exp"] - charge["iat"] == 480 * 60, (
        "le jeton émis doit porter exactement la durée décidée (D6, 480 min)"
    )
    assert re.fullmatch(r"[0-9a-f]{32}", charge["jti"]), (
        "le jeton doit porter un jti révocable (migration 018)"
    )


def test_un_jeton_expire_mais_bien_signe_est_refuse_en_http(client):
    reponse = client.get("/moi", headers=entete_autorisation(_jeton_expire_bien_signe()))
    assert reponse.status_code == 401, reponse.text
    assert "expiré" in reponse.json()["detail"].lower()
    assert "reconnectez" in reponse.json()["detail"].lower()


def test_aucune_route_de_renouvellement_de_session_n_existe(app, client):
    motifs = ("refresh", "renouvel", "renew", "prolong")
    chemins = [getattr(route, "path", "") for route in app.routes]
    for motif in motifs:
        trouvés = [chemin for chemin in chemins if motif in chemin.lower()]
        assert trouvés == [], f"route de renouvellement inattendue : {trouvés}"

    for methode in ("get", "post"):
        reponse = getattr(client, methode)("/auth/refresh")
        assert reponse.status_code == 404, (
            f"{methode.upper()} /auth/refresh : {reponse.status_code} — une "
            "route de renouvellement existerait, contraire à D6"
        )
